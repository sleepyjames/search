import calendar
import datetime


class UTC(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return datetime.timedelta(0)

utc = UTC()


def is_tz_aware(value):
    return value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None


def datetime_to_timestamp(value):
    return calendar.timegm(value.utctimetuple())


def timestamp_to_datetime(value):
    return datetime.datetime.utcfromtimestamp(value)
