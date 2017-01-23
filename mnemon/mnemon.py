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
    # todo: _pickle = False is a shit idea. think of a sane alternative
    _pickle = True

    _expire = None

    def _compress(self, value):
        if self._pickle:
            value = pickle.dumps(value)

        return zlib.compress(value)

    def _decompress(self, value):
        value = zlib.decompress(value)

        if self._pickle:
            value = pickle.loads(value)

        return value

    def __init__(self, expire=None, pickle=False):
        self._expire = expire
        self._pickle = pickle

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

    def __keytransform__(self, key):
        return sha256(key.encode("utf-8")).hexdigest()

    def __enter__(self):
        return self

    def __exit__(self, t, value, traceback):
        pass


try:
    from redis import StrictRedis

    class MnRedis(MnBackend):
        def __init__(self, host="localhost", port=6379, db=0, expire=None,
                     pickle=True):
            super().__init__(expire=expire, pickle=pickle)
            self.d = Redis(host=host, port=port, db=db)

        def __getitem__(self, key):
            return self._decompress(self.d[self.__keytransform__(key)])

        def __setitem__(self, key, value):
            self.d[self.__keytransform__(key)] = self._compress(value)
            if self._expire:
                self.expire(self.__keytransform__(key), self._expire)

        def __delitem__(self, key):
            del self.d[self.__keytransform__(key)]

        def __len__(self):
            # useless
            return len(self.d.keys())

        def expire(self, key, secs=86400):
            self.d.expire(self.__keytransform__(key), secs)

        def bomb(self):
            return self.d.flushall()

except ImportError:
    StrictRedis = None

    class MnRedis(None):
        def __init__(self):
            raise ImportError("'redis' not found. Please install it.")


class MnFile(MnBackend):
    @staticmethod
    def _perms(path):
        return os.chmod(path, 0o777)

    def __init__(self, cachedir=None, expire=None, pickle=True):
        super().__init__(expire=expire, pickle=pickle)
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
                                           self.__keytransform__(key)))

    def __getitem__(self, key):
        if not self.__contains__(key):
            raise KeyError(key)
        return self.get(key)

    def __setitem__(self, key, value):
        if self.__contains__(key):
            del self[key]
        p = os.path.join(self.path, "data", self.__keytransform__(key))
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
        p = os.path.join(self.path, "data", self.__keytransform__(key))
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
        p = os.path.join(self.path, "data", self.__keytransform__(key))
        if not os.path.exists(p):
            pass
        with open(os.path.join(p, "expire"), "w") as expfile:
            expfile.write(str(time.time() + offset))
        self._perms(os.path.join(p, "expire"))

    def get(self, key, **kwargs):
        if not self.__contains__(key):
            return None
        p = os.path.join(self.path, "data", self.__keytransform__(key))
        with open(os.path.join(p, "data"), "rb") as f:
            v = self._decompress(f.read())
        return v

    def bomb(self):
        if os.path.exists(self.path):
            shutil.rmtree(self.path)


def mnemon(be="redis", **kwargs):
    if be not in {"file", "redis"}:
        raise NotImplementedError(be)

    if be == "redis":
        try:
            rc = MnRedis(**kwargs)
            rc.d.ping()
            return rc
        except (ImportError, RedisConnectionError):
            # todo: something not too invasive to point out the 'file' fallback
            pass

    return MnFile(**kwargs)
