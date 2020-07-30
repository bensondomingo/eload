default_app_config = 'cphapp.apps.CphappConfig'

import redis as _redis
redis = _redis.Redis(db=1)

__exclude__ = [_redis]