"""
Heal Process

Roll through videos, check for completion
    - reencode endpoints
    - fix data (if wrong), including on VAL
    - reschedule self

"""
import datetime
import uuid
from datetime import timedelta

import yaml
from django.utils.timezone import utc

import celeryapp
from control_env import *
from veda_encode import VedaEncode
from veda_val import VALAPICall

time_safetygap = datetime.datetime.utcnow().replace(tzinfo=utc) - timedelta(days=1)


class VedaHeal(object):
    """
    Maintenance process for finding and repairing failed encodes

    """
    def __init__(self, **kwargs):
        self.current_time = datetime.datetime.utcnow().replace(tzinfo=utc)
        self.auth_yaml = kwargs.get(
            'auth_yaml',
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'instance_config.yaml'
            ),
        )
        self.auth_dict = self._READ_AUTH()
        # for individuals
        self.video_query = kwargs.get('video_query', None)
        self.freezing_bug = kwargs.get('freezing_bug', True)
        self.val_status = None
        self.retry_barrier_hours = 24

    def _READ_AUTH(self):
        if self.auth_yaml is None:
            return None
        if not os.path.exists(self.auth_yaml):
            return None

        with open(self.auth_yaml, 'r') as stream:
            try:
                auth_dict = yaml.load(stream)
                return auth_dict
            except yaml.YAMLError as exc:
                return None

    def discovery(self):
        self.video_query = Video.objects.filter(
            video_trans_start__lt=self.current_time - timedelta(
                hours=self.auth_dict['heal_start']
            ),
            video_trans_start__gt=self.current_time - timedelta(
                hours=self.auth_dict['heal_end']
            )
        )

        self.send_encodes()

    def send_encodes(self):
        for v in self.video_query:
            encode_list = self.determine_fault(video_object=v)
            # Using the 'Video Proto' Model
            if self.val_status is not None:
                VAC = VALAPICall(
                    video_proto=None,
                    video_object=v,
                    val_status=self.val_status,
                )
                VAC.call()
            self.val_status = None

            if len(encode_list) > 0:
                """
                send job to queue
                """
                if v.video_orig_filesize > self.auth_dict['largefile_queue_barrier']:
                    cel_queue = self.auth_dict['largefile_celery_queue']
                else:
                    cel_queue = self.auth_dict['main_celery_queue']

                for e in encode_list:
                    veda_id = v.edx_id
                    encode_profile = e
                    jobid = uuid.uuid1().hex[0:10]
                    celeryapp.worker_task_fire.apply_async(
                        (veda_id, encode_profile, jobid),
                        queue=cel_queue
                    )

    def determine_fault(self, video_object):
        """
        Determine expected and completed encodes
        """
        if self.freezing_bug is True:
            if video_object.video_trans_status == 'Corrupt File':
                return []

        if video_object.video_trans_status == 'Review Reject':
            return []

        if video_object.video_trans_status == 'Review Hold':
            return []

        if video_object.video_active is False:
            return []

        """
        Finally, determine encodes
        """
        uncompleted_encodes = VedaEncode(
            course_object=video_object.inst_class,
            veda_id=video_object.edx_id
        ).determine_encodes()
        expected_encodes = VedaEncode(
            course_object=video_object.inst_class,
        ).determine_encodes()
        try:
            uncompleted_encodes.remove('review')
        except KeyError:
            pass

        # list comparison
        return self.differentiate_encodes(uncompleted_encodes, expected_encodes, video_object)

    def differentiate_encodes(self, uncompleted_encodes, expected_encodes, video_object):
        """
        Update video status if complete
        """
        # Video Status Updating
        check_list = []
        if uncompleted_encodes is not None:
            for e in uncompleted_encodes:
                # These encodes don't count towards 'file_complete'
                if e != 'mobile_high' and e != 'audio_mp3' and e != 'review':
                    check_list.append(e)
        if check_list is None or len(check_list) == 0:
            self.val_status = 'file_complete'
            # File is complete!
            # Check for data parity, and call done
            if video_object.video_trans_status != 'Complete':
                Video.objects.filter(
                    edx_id=video_object.edx_id
                ).update(
                    video_trans_status='Complete',
                    video_trans_end=datetime.datetime.utcnow().replace(tzinfo=utc)
                )
        if not uncompleted_encodes or len(uncompleted_encodes) == 0:
            return []

        if self.freezing_bug:
            if self.determine_longterm_corrupt(uncompleted_encodes, expected_encodes, video_object):
                return []

        if self.val_status != 'file_complete':
            self.val_status = 'transcode_queue'
        return uncompleted_encodes

    def determine_longterm_corrupt(self, uncompleted_encodes, expected_encodes, video_object):
        """
        get baseline // if there are == encodes and baseline,
        mark file corrupt -- just run the query again with
        no veda_id
        """

        try:
            expected_encodes.remove('hls')
        except ValueError:
            pass
        # Mark File Corrupt, accounting for migrated URLs
        if len(expected_encodes) == len(uncompleted_encodes) - 1 and len(expected_encodes) > 1:
            try:
                url_test = URL.objects.filter(
                    videoID=Video.objects.filter(
                        edx_id=video_object.edx_id
                    ).latest()
                ).exclude(
                    encode_profile=Encode.objects.get(
                        product_spec='hls'
                    )
                )
            except AttributeError:
                url_test = []
            retry_barrier = datetime.datetime.utcnow().replace(tzinfo=utc) - timedelta(hours=self.retry_barrier_hours)

            if video_object.video_trans_start < retry_barrier:
                if len(url_test) < 1:
                    try:
                        Video.objects.filter(
                            edx_id=video_object.edx_id
                        ).update(
                            video_trans_status='Corrupt File',
                            video_trans_end=datetime.datetime.utcnow().replace(tzinfo=utc)
                        )
                    except AttributeError:
                        pass
                    self.val_status = 'file_corrupt'
                    return True
        return False

    def purge(self):
        """
        Purge Work Directory

        """
        for file in os.listdir(WORK_DIRECTORY):
            full_filepath = os.path.join(WORK_DIRECTORY, file)
            filetime = datetime.datetime.utcfromtimestamp(
                os.path.getmtime(
                    full_filepath
                )
            ).replace(tzinfo=utc)
            if filetime < time_safetygap:
                print file + " : WORK PURGE"
                os.remove(full_filepath)


def main():
    VH = VedaHeal()
    VH.discovery()

if __name__ == '__main__':
    sys.exit(main())
