import os
import sys

from pymilvus import DataType, Function, FunctionType, MilvusClient

# 上级目录路径的绝对路径

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Adjust the path to import config
from config import MILVUS_DB_NAME, MILVUS_HOST


def create_milvus_collections():
    # Initialize the Milvus client
    client = MilvusClient(uri=MILVUS_HOST, db_name=MILVUS_DB_NAME)

    schema = MilvusClient.create_schema(auto_id=True)

    schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
    schema.add_field(field_name="dense", datatype=DataType.FLOAT_VECTOR, dim=1024)
    schema.add_field(field_name="code", datatype=DataType.VARCHAR, max_length=64)
    schema.add_field(field_name="model", datatype=DataType.VARCHAR, max_length=64)
    schema.add_field(field_name="type", datatype=DataType.VARCHAR, max_length=64)
    schema.add_field(field_name="series", datatype=DataType.VARCHAR, max_length=64)
    schema.add_field(field_name="description", datatype=DataType.VARCHAR, max_length=256)
    schema.add_field(field_name="luminous_flux", datatype=DataType.VARCHAR, max_length=64)
    schema.add_field(field_name="size", datatype=DataType.VARCHAR, max_length=64)
    schema.add_field(field_name="beam_angle", datatype=DataType.VARCHAR, max_length=64)
    schema.add_field(field_name="color_temp", datatype=DataType.VARCHAR, max_length=64)
    schema.add_field(field_name="hole_size", datatype=DataType.VARCHAR, max_length=64)
    schema.add_field(field_name="power", datatype=DataType.VARCHAR, max_length=64)

    index_params = client.prepare_index_params()

    index_params.add_index(
        field_name="id",
        index_type="AUTOINDEX"
    )

    index_params.add_index(
        field_name="dense", 
        index_type="AUTOINDEX",
        metric_type="COSINE"
    )
    
    client.create_collection(
        collection_name="products",
        schema=schema,
        index_params=index_params
    )

    res = client.get_load_state(
        collection_name="products",
    )

    print(res)

    return

if __name__ == "__main__":

    create_milvus_collections()
