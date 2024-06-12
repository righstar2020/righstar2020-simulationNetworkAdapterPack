
import asyncio,time
from tinydb import TinyDB, Query,where
from tinydb.storages import MemoryStorage
from concurrent.futures import ThreadPoolExecutor
import logging
logging.basicConfig(level=logging.INFO)
class TinyDBUtil:
    def __init__(self):
        self.db_path = None
        pass
    async def init_db(self):
        self.db_path = "db.json"
        data = {"author": "rightstar", "version": '1.0'}
        await self.async_upsert_by_key( "config", data,"version",'1.0')
        logging.info("init tinydb success.")
        logging.info(f"db path:{self.db_path}")
    async def async_upsert_by_key(self, table_name, data, fieldName, value):
        #为数据增加或更新时间戳
        data['timestamp']=int(round(time.time() * 1000))
        db = TinyDB(self.db_path)
        table = db.table(table_name)
        query = Query()
        doc_ids = [doc.doc_id for doc in table.search(query[fieldName] == value)]
        # 如果找到了匹配的文档，则更新
        if doc_ids:
            table.update(data, doc_ids=doc_ids)
            logging.info(f"Updated existing document(s) with {fieldName}={value}.")
        else:
            # 如果没有找到匹配的文档，则插入新数据
            table.insert(data)
            logging.info(f"Inserted new document with {fieldName}={value} as no existing match was found.")
        db.close()
    async def async_write(self, table_name, data):
        db = TinyDB(self.db_path)
        table = db.table(table_name)
        table.insert(data)
        db.close()
        
    async def async_timely_write(self, table_name, data):
        
        #为数据增加时间戳(精确到ms)
        data['timestamp']=int(round(time.time() * 1000))
        return await self.async_write(table_name, data)
    async def async_read(self, table_name, query=None):

        db = TinyDB(self.db_path)
        table = db.table(table_name)
        if query:
            result = table.search(query)
        else:
            result = table.all()
        db.close()
        return result
    
    async def async_read_sort_by_timestamp(self, table_name, limit = 0,order_by_time = False,  field_name=None, field_value = None):
      
        db = TinyDB(self.db_path)
        table = db.table(table_name)
        
        if field_name:
            # 构造查询，例如查询字段名为'field_name'且值为'value'
            query = where(field_name) == field_value  # 注意：这里'value'需要替换成实际值或从参数中获取
            results = table.search(query)
        else:
            results = table.all()
        
        # 如果需要按时间排序，这里假设每个文档都有一个名为'timestamp'的时间戳字段
        if order_by_time:
            results.sort(key=lambda x: x['timestamp'])  # 假设时间戳字段名为'timestamp'
            # 如果需要降序，可以改为: results.sort(key=lambda x: x['timestamp'], reverse=True)           
        db.close()
        #返回指定数量的结果
        if limit > 0:
            results = results[:limit]
        return results
    
    async def async_read_by_key_value(self, table_name,field_name=None, field_value = None):
      
        db = TinyDB(self.db_path)
        table = db.table(table_name)
        results=[]
        if field_name:
            # 构造查询，例如查询字段名为'field_name'且值为'value'
            query = where(field_name) == field_value  # 注意：这里'value'需要替换成实际值或从参数中获取
            results = table.search(query)
            
        if len(results)>0:
            return results
        return None
       
