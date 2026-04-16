import pandas as pd
import numpy as np
import os
import difflib
import requests
from pymilvus import MilvusClient

from config import MILVUS_HOST, MILVUS_DB_NAME, MILVUS_COLLECTION_NAME, MILVUS_TOKEN, API_KEY

class ProductRetrievalService:
    """Service for fuzzy product retrieval using Milvus vector search (Remote Embedding)."""
    
    def __init__(self, model_name: str = "text-embedding-v3", collection_name: str = None, partition_name: str = None):
        self.model_name = model_name
        self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
        
        # Initialize Milvus Client
        print(f"Connecting to Milvus at {MILVUS_HOST}...")
        self.client = MilvusClient(uri=MILVUS_HOST, db_name=MILVUS_DB_NAME, token=MILVUS_TOKEN)
        self.collection_name = collection_name or MILVUS_COLLECTION_NAME
        self.partition_name = partition_name

    def _get_embedding(self, text: str):
        """Calls Aliyun DashScope API to get vector."""
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "input": {"texts": [text]},
            "parameters": {"dimension": 1024}
        }
        response = requests.post(self.api_url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["output"]["embeddings"][0]["embedding"]
        else:
            raise Exception(f"Embedding API failed: {response.text}")

    def search(self, query: str, top_k: int = 5, filters: dict = None):
        """
        Searches for products using Hybrid Search (Milvus Vector + Local Lexical Boost).
        """
        if not query:
            return []
            
        # 1. Preprocessing
        clean_query = query
        for suffix in ["系列", "款", "系统", "一代", "二代", "三代", "四代"]:
            clean_query = clean_query.replace(suffix, "")
        clean_query = clean_query.strip()
            
        # 2. Vector Search via Milvus (Invoke Remote API)
        query_embedding = self._get_embedding(clean_query)
        
        # Prepare Milvus filter expression
        expr = None
        if filters:
            conditions = []
            for k, v in filters.items():
                conditions.append(f"{k} == '{v}'")
            expr = " and ".join(conditions)
            
        # Search in Milvus
        try:
            search_params = {
                "collection_name": self.collection_name,
                "data": [query_embedding],
                "filter": expr,
                "limit": top_k * 3, # Fetch slightly more for local reranking
                "output_fields": ["materialCode", "category1", "category2", "series", "description", "power", "colorTemp", "industyLevel", "cri", "lumen", "size", "beamAngle", "holeSize", "assemble", "pricePosition", "ugr"]
            }
            if self.partition_name:
                search_params["partition_names"] = [self.partition_name]
                
            search_res = self.client.search(**search_params)
        except Exception as e:
            print(f"Milvus search error: {e}")
            return []
        
        if not search_res or len(search_res[0]) == 0:
            return []
            
        # 3. Local Lexical Boost (Reranking)
        results = []
        for hit in search_res[0]:
            entity = hit['entity']
            # Milvus COSINE distance is similarity (if metric is COSINE)
            # pymilvus-lite/standalone might return distance differently depending on metric.
            vector_score = hit['distance']
            
            series_name = str(entity.get('series', ''))
            lexical_sim = difflib.SequenceMatcher(None, clean_query, series_name).ratio()
            
            # Boost strategy
            final_score = vector_score
            if clean_query in series_name or series_name in clean_query:
                final_score += 0.5
            else:
                final_score += lexical_sim * 0.3
                
            entity['score'] = final_score
            results.append(entity)
            
        # Sort by total score and return top_k
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]

# Singleton instance for global use
_instance = None
def get_product_retriever(partition_name="office"):
    global _instance
    if _instance is None:
        _instance = ProductRetrievalService(partition_name=partition_name)
    return _instance
