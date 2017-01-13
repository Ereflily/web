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
        primary_key = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info("found mapping: {} ==> {}".format(k, v))
                mappings[k] = v
                if v.primary_key:
                    if primary_key:
                        raise SQLError('Duplicate primary key for field: {}'.format(k))
                    primary_key = k
                else:
                    fields.append(k)
        if not primary_key:
            raise SQLError('have no primary for this table')
        for k in mappings:
            attrs.pop(k)
        escapeFiled = list(map(lambda f: '`{}`'.format(f), fields))
        attrs['__table__'] = tableName
        attrs['__where__'] = []
        attrs['__args__'] = {}
        attrs['__primaryKey__'] = primary_key
        attrs['__fields__'] = fields
        attrs['__select__'] = []
        attrs['__limit__'] = []

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
                value = field.default() if callable(field.default()) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value

    @classmethod
    def find(cls):
        if cls.__name__ == 'Model':
            raise ValueError("can not use Model")
        return cls()

    def where(self, params):
        if isinstance(params, list):
            for param in params:
                if len(param) > 2:
                    self.__where__.append("`{}` {} ?".format(param[0],param[2]))
                    self.__args__['where'].append(param[1])
                elif len(param) == 2:
                    self.__where__.append("`{}` = ?".format(param[0]))
                    self.__args__['where'].append(param[1])
        else:
            raise ValueError("condition must be a list")
        return self

    async def all(self):
        sql = []
        if len(self.__select__) > 0:
            sql.append("select {} from {}".format(','.join(self.__select__), self.__table__))
        else:
            sql.append("select * from {}".format(self.__table__))
        args = []
        if len(self.__where__) > 0:
            sql.append('where')
            sql.append(' and '.join(self.__where__))
            args.extend(self.__args__['where'])
        if len(self.__limit__) > 0:
            sql.append('limit')
            sql.extend(self.__limit__)
        rs = await select(' '.join(sql), args)
        if len(rs) == 0:
            return None
        return [self.__class__(**r) for r in rs]

    def choose(self, params):
        if isinstance(params, list):
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

    @classmethod
    async def findNum(cls, selectFiled, where=None, args=None):
        sql = ['select count(`{}`) __num__ from `{}`'.format(selectFiled, cls.__table__)]
        if args is None:
            args = []
        if where:
            sql.append('where')
            if isinstance(where, dict):
                if len(where) > 1:
                    sql.append(' and '.join(map(lambda f: '`{}` = "?"'.format(f), list(where.keys()))))
                else:
                    sql.append('`{}` = "?"'.format(list(where.keys())[0]))
                args.extend(list(where.values()))
            else:
                raise ValueError(r'where must be a dict')

        rs = await select(' '.join(sql), args)
        if len(rs) == 0:
            return None
        return rs[0]['__num__']

    async def save(self):
        args = list()
        args.append(self.getValueOrDefault(self.__primaryKey__))
        args.extend(list(map(self.getValueOrDefault, self.__fields__)))
        rs = await execute(self.__insert__, args)
        if rs != 1:
            logging.warning('failed to insert record: affected rows: %s' % rs)

    async def update(self, where=None):
        sql = list(self.__update__)
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        if where:
            sql.append('where')
            if isinstance(where, dict):
                if len(where) > 1:
                    sql.append(' and '.join(map(lambda f: '`{}` = "?"'.format(f), list(where.keys()))))
                else:
                    sql.append('`{}` = "?"'.format(list(where.keys())[0]))
                args.extend(list(where.values()))
            else:
                raise ValueError(r'where must be a dict')
        rs = await execute(' '.join(sql), args)
        if rs < 1:
            logging.warning('failed to update')

    async def remove(self, where=None):
        sql = list(self.__delete__)
        args = []
        if where:
            sql.append('where')
            if isinstance(where, dict):
                if len(where) > 1:
                    sql.append(' and '.join(map(lambda f: '`{}` = "?"'.format(f), list(where.keys()))))
                else:
                    sql.append('`{}` = "?"'.format(list(where.keys())[0]))
                args.extend(list(where.values()))
            else:
                raise ValueError(r'where must be a dict')
        rs = await execute(' '.join(sql), args)
        if rs < 1:
            logging.warning("delete failed")


if __name__ == '__main__':
    class User(Model):
        id = IntegerField('id', primary_key=True)
        name = StringField('name')

    user = User(id=1, name='hello')
    loop = asyncio.get_event_loop()


    async def test(loop):
        await create_pool(loop, db='test')
        s = await user.find().where([['id',1,'>=']]).choose(['id']).limit(1).all()
        print(s)
        exit()


    loop.run_until_complete(test(loop))
    loop.close()
    exit()
