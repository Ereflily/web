# -*- coding: utf-8 -*-
__author__ = 'Ernie Peng'

import asyncio, logging, aiomysql, sys


def log(sql, args=()):
    print('SQL: {}'.format(sql))

async def create_pool(loop, **kw):
    logging.info("create datebase connection pool....")
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw.get('user', 'root'),
        password=kw.get('password', ''),
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop
    )

async def close_pool():
    global __pool
    if __pool is not None:
        __pool.close()
        await __pool.wait_closed()

async def select(sql, args, size=None):
    log(sql, args)
    global __pool
    async with __pool.get() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace('?', '%s'), args or ())
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
            await cur.close()
        logging.info("rows return:{}".format(len(rs)))
        conn.close()
    #await close_pool()
        return rs

async def execute(sql, args, autocommit=True):
    log(sql, args)
    global __pool
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', '%s'), args)
                affect = cur.rowcount
                if not autocommit:
                    await conn.commit()
                    await cur.close()
        except:
            if not autocommit:
                await conn.rollback()
            affect = 0
        conn.close()
    #await close_pool()
        return affect


def create_args_string(num):
    argsList = []
    for x in range(num):
        argsList.append('?')
    return ','.join(argsList)


class Field():
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return "{}, {}:{}".format(self.__class__.__name__, self.column_type, self.name)


class StringField(Field):
    def __init__(self, name=None, primary_key=False, default='', type='varchar(255)'):
        super().__init__(name, type, primary_key, default)


class BooleanField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'Boolean', False, default)


class IntegerField(Field):
    def __init__(self, name=None, primary_key=False, default=0, type='int'):
        super().__init__(name, type, primary_key, default)


class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0, type='float'):
        super().__init__(name, type, primary_key, default)


class TextField(Field):
    def __init__(self, name=None, default='', type='text'):
        super().__init__(name, type, False, default)


class SQLError(Exception):
    def __init__(self, value):
        self.__error__ = value

    def __str__(self):
        return repr(self.__error__)


class ModelMetaClass(type):
    def __new__(cls, name, base, attrs):
        if name == 'Model':
            return type.__new__(cls, name, base, attrs)
        tableName = attrs.get('__table__', None) or name
        logging.info("found Model : {}(table {})".format(name, tableName))
        mappings = dict()
        fields = []
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info("found mapping: {} ==> {}".format(k, v))
                mappings[k] = v
                fields.append(k)
        for k in mappings:
            attrs.pop(k)
        escapeFiled = list(map(lambda f: '`{}`'.format(f), fields))
        attrs['__table__'] = tableName
        attrs['__where__'] = []
        attrs['__args__'] = {}
        attrs['__fields__'] = fields
        attrs['__mappings__'] = mappings
        attrs['__select__'] = []
        attrs['__limit__'] = []
        attrs['__orderBy__'] = []
        attrs['__sql__'] = []
        attrs['__update__'] = []
        attrs['__insert__'] = "insert into `{}`({}) VALUES({}) ".format(tableName, ','.join(escapeFiled), create_args_string(len(fields)))
        attrs['__delete__'] = "delete from {}".format(tableName)
        return type.__new__(cls, name, base, attrs)


class Model(dict, metaclass=ModelMetaClass):
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)
        self.__args__['where'] = []

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = self.getValue(key)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value

    @classmethod
    def find(cls):
        if cls.__name__ == 'Model':
            raise ValueError("can not use Model")
        return cls()

    def where(self, *params):
        for param in params:
            if isinstance(param, list):
                if len(param) > 2:
                    self.__where__.append("`{}` {} ?".format(param[0],param[2]))
                    self.__args__['where'].append(param[1])
                elif len(param) == 2:
                    self.__where__.append("`{}` = ?".format(param[0]))
                    self.__args__['where'].append(param[1])
            else:
                if len(params) > 2:
                    self.__where__.append("`{}` {} ?".format(params[0], params[2]))
                    self.__args__['where'].append(params[1])
                elif len(params) == 2:
                    self.__where__.append("`{}` = ?".format(params[0]))
                    self.__args__['where'].append(params[1])
                break
        return self

    async def all(self):
        if len(self.__select__) > 0:
            self.__sql__.append("select {} from {}".format(','.join(self.__select__), self.__table__))
        else:
            self.__sql__.append("select * from {}".format(self.__table__))
        args = []
        if len(self.__where__) > 0:
            self.__sql__.append('where')
            self.__sql__.append(' and '.join(self.__where__))
            args.extend(self.__args__['where'])
        if len(self.__orderBy__) > 0:
            self.__sql__.append('order by')
            self.__sql__.extend(self.__orderBy__)
        if len(self.__limit__) > 0:
            self.__sql__.append('limit')
            self.__sql__.extend(self.__limit__)
        rs = await select(' '.join(self.__sql__), args)
        if len(rs) == 0:
            return None
        return [self.__class__(**r) for r in rs]

    def choose(self, *params):
        self.__select__.append(','.join(params))
        return self

    def limit(self, params):
        if isinstance(params, list):
            if len(params) == 2:
                self.__limit__.append(','.join(params))
            else:
                raise ValueError("too much parameters")
        elif isinstance(params, int):
            self.__limit__.append(str(params))
        else:
            raise ValueError("error type of parameters")
        return self

    def orderBy(self, params):
        if isinstance(params, list):
            self.__orderBy__.append("{} {}".format(params[0], params[1]))
        return self

    async def count(self):
        self.__sql__.append("select count(*) as cnt from {}".format(self.__table__))
        args = []
        if len(self.__where__) > 0:
            self.__sql__.append('where')
            self.__sql__.append(' and '.join(self.__where__))
            args.extend(self.__args__['where'])
        rs = await select(' '.join(self.__sql__), args)
        return rs[0]['cnt']

    async def save(self):
        args = list()
        args.extend(list(map(self.getValueOrDefault, self.__fields__)))
        rs = await execute(self.__insert__, args)
        if rs != 1:
            logging.warning('failed to insert record: affected rows: %s' % rs)
            return False
        return True

    async def update(self, *params):
        args = []
        for param in params:
            self.__update__.append("`{}` = ?".format(param[0]))
            args.append(param[1])
        self.__sql__.append("update {} set {}".format(self.__table__, ','.join(self.__update__)))
        if len(self.__where__) > 0:
            self.__sql__.append('where')
            self.__sql__.append(' and '.join(self.__where__))
            args.extend(self.__args__['where'])
        rs = await execute(' '.join(self.__sql__), args)
        if rs == 0:
            logging.warning("fail to update record: affect rows {}".format(rs))
            return False
        return True

    async def remove(self):
        self.__sql__.append(self.__delete__)
        args = []
        if len(self.__where__) > 0:
            self.__sql__.append('where')
            self.__sql__.append(' and '.join(self.__where__))
            args.extend(self.__args__['where'])
        rs = await execute(' '.join(self.__sql__), args)
        if rs < 1:
            logging.warning("delete failed")
            return False
        return True


if __name__ == '__main__':
    class User(Model):
        id = IntegerField('id', primary_key=True)
        name = StringField('name')

    user = User(id=1, name='hello')
    loop = asyncio.get_event_loop()


    async def test(loop):
        await create_pool(loop, db='test')
        s = await user.where(['id',1]).update(['name','hello1'])
        #await user.save()
        print(s)
        exit()


    loop.run_until_complete(test(loop))
    loop.close()
    exit()
