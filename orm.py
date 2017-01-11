__author__ = 'Ernie Peng'

import asyncio, logging, aiomysql

def log(sql, args = ()):
    logging.info('SQL: {}'.format(sql))

async def create_pool(loop, **kw):
    logging.info("create datebase connection pool....")
    global __pool
    __pool = await aiomysql.create_pool(
        host = kw.get('host', 'localhost'),
        port = kw.get('port', '3306'),
        user = kw.get('user', 'root'),
        password = kw.get('password'),
        db = kw.get('db'),
        charset = kw.get('charset', 'utf-8'),
        autocommit = kw.get('autocommit', True),
        maxsize = kw.get('maxsize', 10),
        minsize = kw.get('minsize', 0),
        loop = loop
    )

async def select(sql, args, size = None):
    log(sql, args)
    global __pool
    async with __pool.get() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace('?', '%s'), args or ())
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
        logging.info("rows return:{}".format(len(rs)))
        return rs

async def execute(sql, args, autocommit = True):
    log(sql, args)
    global __pool
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replce('?', '%s'), args)
                affect = cur.rowcount
                if not autocommit:
                    await conn.commit()
        except Exception as e:
            if not autocommit:
                await conn.rollback()
            raise
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

class StringFile(Field):
    def __init__(self, name = None, primary_key = False, default = '', type = 'varchar(255)'):
        super().__init__(name, type, primary_key, default)

class BooleanField(Field):
    def __init__(self, name = None, default = None):
        super().__init__(name, 'Boolean', False,default)

class IntegerField(Field):
    def __init__(self, name = None, primary_key = False, default = 0, type = 'int'):
        super().__init__(name,type, primary_key,default)

class FloatField(Field):
    def __init__(self, name = None, primary_key = False, default = 0.0, type = 'float'):
        super().__init__(name, type, primary_key, default)

class TextField(Field):
    def __init__(self, name = None, default = '', type = 'text'):
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
        attrs['__primaryKey__'] = primary_key
        attrs['__fileds__'] = fields
        attrs['__select__'] = "select `{}`,{} from {}".format(primary_key, ','.join(escapeFiled), tableName)
        attrs['__insert__'] = "insert into `{}` (`{}`,{}) values({})".format(tableName, primary_key, ','.join(escapeFiled), create_args_string(len(escapeFiled) + 1))
        attrs['__update__'] = "update {} set {} where `{}` = ?".format(tableName, ','.join(map(lambda f: '{} = {}'.format(mappings[f] or f),fields)), primary_key)
        attrs['__delete__'] = "delete from {} where `{}` = ?".format(tableName, primary_key)
        return type.__new__(cls, name, base, attrs)

class Model(dict, metaclass = ModelMetaClass):
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

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
    async def findAll(cls, where = None, args = None, **kw):
        if cls.__name__ == 'Model':
            raise SQLError("can not use Model")
        sql = [cls.__select__]
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
        if args is None:
            args = []
        orderby = kw.get('orderby', None)
        if orderby is not None:
            if isinstance(orderby, dict):
                sql.append('order by')
                if len(orderby) > 1:
                    sql.append(','.join(map(lambda f: "`{}` {}".format(f, orderby[f]), orderby.keys())))
                else:
                    sql.append("`{}` {}".format(list(orderby.keys()[0]), list(orderby.values()[0])))
            else:
                raise ValueError(r'orderby must be dict')
        limit = kw.get('limit', None)
        if limit:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?,?')
                args.extend(limit)
        rs = await select(' '.join(sql), args)
        return [cls(**r) for r in rs]