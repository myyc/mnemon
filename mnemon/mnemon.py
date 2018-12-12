from collections import MutableMapping
from hashlib import sha256
import pickle
import zlib
import os
import shutil
import time

import appdirs
from redis import Redis


try:
    from redis.exceptions import ConnectionError as RedisConnectionError
except ImportError:
    RedisConnectionError = BaseException


class MnBackend(MutableMapping):
    _raw = False
    _expire = None

    def _compress(self, value):
        if not self._raw:
            value = pickle.dumps(value)
        elif type(value) is not bytes:
            if type(value) is str:
                value = value.encode("utf-8")
            else:
                raise TypeError(type(value))

        return zlib.compress(value)

    def _decompress(self, value):
        value = zlib.decompress(value)

        if not self._raw:
            value = pickle.loads(value)

        return value

    def __init__(self, expire=None, raw=False):
        self._expire = expire
        self._raw = raw

    def __getitem__(self, key):
        pass

    def __setitem__(self, key, value):
        pass

    def __delitem__(self, key):
        pass

    def __iter__(self):
        raise NotImplementedError("No.")

    def __len__(self):
        pass

    @staticmethod
    def _hash(key):
        if type(key) is not str:
            key = str(key)
        return sha256(key.encode("utf-8")).hexdigest()

    def __enter__(self):
        return self

    def __exit__(self, t, value, traceback):
        pass


try:
    from redis import StrictRedis

    # noinspection PyAbstractClass
    class MnRedis(MnBackend):
        def __init__(self, host="localhost", port=6379, db=0, expire=None,
                     raw=False):
            super().__init__(expire=expire, raw=raw)
            self.d = Redis(host=host, port=port, db=db)

        def __getitem__(self, key):
            return self._decompress(self.d[self._hash(key)])

        def __setitem__(self, key, value):
            self.d[self._hash(key)] = self._compress(value)
            if self._expire:
                self.expire(self._hash(key), self._expire)

        def __delitem__(self, key):
            del self.d[self._hash(key)]

        def __len__(self):
            # useless
            return len(self.d.keys())

        def expire(self, key, secs=86400):
            self.d.expire(self._hash(key), secs)

        def bomb(self):
            return self.d.flushall()

except ImportError:
    StrictRedis = None

    class MnRedis(None):
        def __init__(self):
            raise ImportError("'redis' not found. Please install it.")


# noinspection PyAbstractClass
class MnFile(MnBackend):
    @staticmethod
    def _perms(path):
        return os.chmod(path, 0o777)

    def __init__(self, cachedir=None, expire=None, raw=False):
        super().__init__(expire=expire, raw=raw)
        cd = cachedir or appdirs.user_cache_dir(appname="mnemon",
                                                appauthor="myyc")
        self.path = cd

        if not os.path.exists(cd):
            os.mkdir(self.path)
            self._perms(self.path)
            os.mkdir(os.path.join(self.path, "data"))
            self._perms(os.path.join(self.path, "data"))

        self._cleanup()

    def __enter__(self):
        return self

    def __exit__(self, t, value, traceback):
        if os.path.exists(self.path):
            self._cleanup()

    def __contains__(self, key):
        return os.path.exists(os.path.join(self.path, "data",
                                           self._hash(key)))

    def __getitem__(self, key):
        if not self.__contains__(key):
            raise KeyError(key)
        return self.get(key)

    def __setitem__(self, key, value):
        if self.__contains__(key):
            del self[key]
        p = os.path.join(self.path, "data", self._hash(key))
        os.mkdir(p)
        self._perms(p)
        with open(os.path.join(p, "key"), "w") as fk:
            fk.write(key)
        self._perms(os.path.join(p, "key"))
        with open(os.path.join(p, "data"), "wb") as f:
            f.write(self._compress(value))
        self._perms(os.path.join(p, "data"))

    def __delitem__(self, key):
        if not self.__contains__(key):
            pass
        p = os.path.join(self.path, "data", self._hash(key))
        shutil.rmtree(p)

    def __len__(self):
        return len(os.listdir(os.path.join(self.path, "data")))

    def _cleanup(self):
        for f in os.listdir(os.path.join(self.path, "data")):
            epath = os.path.join(self.path, "data", f, "expire")
            if os.path.exists(epath):
                with open(epath, "r") as efile:
                    expdate = float(efile.read())
                    if expdate < time.time():
                        shutil.rmtree(os.path.join(self.path, "data", f))

    def expire(self, key, offset):
        p = os.path.join(self.path, "data", self._hash(key))
        if not os.path.exists(p):
            pass
        with open(os.path.join(p, "expire"), "w") as expfile:
            expfile.write(str(time.time() + offset))
        self._perms(os.path.join(p, "expire"))

    def get(self, key, **kwargs):
        if not self.__contains__(key):
            return None
        p = os.path.join(self.path, "data", self._hash(key))
        with open(os.path.join(p, "data"), "rb") as f:
            v = self._decompress(f.read())
        return v

    def bomb(self):
        if os.path.exists(self.path):
            shutil.rmtree(self.path)


def mnemon(be="any", **kwargs):
    if be not in {"file", "redis", "any"}:
        raise NotImplementedError(be)

    if be == "redis" or be == "any":
        try:
            rc = MnRedis(**kwargs)
            rc.d.ping()
            return rc
        except (ImportError, RedisConnectionError) as e:
            if be == "redis":
                raise e

    return MnFile(**kwargs)
