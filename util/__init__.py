import subprocess


def get_username():
    return subprocess.run("id -un", shell=True, capture_output=True).stdout.decode().strip()


class AttributeDict(dict):
    @classmethod
    def potentially_cast(cls, item):
        if type(item) == dict:
            return AttributeDict(item)
        if hasattr(item, '__iter__'):
            return type(item)([AttributeDict.potentially_cast(x) for x in item])
        return item

    def __getattr__(self, att):
        res = self.__getitem__(att)
        return AttributeDict.potentially_cast(res)
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
