from datetime import date
from itertools import permutations
import polars as pl
import pytest
from fastapi.testclient import TestClient
from app.analysis import build_pivot
from app.data import generate_sales
from app.main import create_app

@pytest.fixture
def data():
    return pl.DataFrame({'Tarih':[date(2025,1,1),date(2025,1,1),date(2025,1,2),date(2025,1,2)], 'Bolge':['Ege','Ege','Marmara','Ege'],'Kategori':['Gida','Gida','Giyim','Giyim'],'Satis_Adedi':[10,20,5,7]})

def test_exact_cells(data):
    r=build_pivot(data,'Bolge','Kategori')
    assert r['data']==[{'Bolge':'Ege','Gida':30,'Giyim':7},{'Bolge':'Marmara','Gida':0,'Giyim':5}]
    assert r['meta']['matched_rows']==4

@pytest.mark.parametrize('row,column',list(permutations(['Tarih','Bolge','Kategori'],2)))
def test_all_axes_with_python_oracle(data,row,column):
    expected={}
    for rec in data.to_dicts():
        key=(str(rec[row]),str(rec[column]))
        expected[key]=expected.get(key,0)+rec['Satis_Adedi']
    r=build_pivot(data,row,column)
    for rec in r['data']:
        for col in r['columns'][1:]:
            assert rec[col]==expected.get((rec[row],col),0)
    assert sum(rec[col] for rec in r['data'] for col in r['columns'][1:])==42

def test_dates_and_empty(data):
    r=build_pivot(data,'Bolge','Kategori',date(2025,1,2),date(2025,1,2))
    assert r['meta']['total_sales']==12
    assert r['meta']['matched_rows']==2
    r=build_pivot(data,'Bolge','Kategori',date(2026,1,1))
    assert r['data']==[] and r['meta']['total_sales']==0

@pytest.fixture
def client():
    with TestClient(create_app(rows=2000)) as c:
        yield c

@pytest.mark.parametrize('query',['row=wrong','row=Bolge&column=Bolge','start_date=no-date','start_date=2025-02-01&end_date=2025-01-01'])
def test_invalid_requests(client,query):
    assert client.get('/pivot?'+query).status_code==422

def test_lifecycle_schema_docs(client):
    assert client.get('/health').json()=={'status':'ok','rows':2000}
    assert client.get('/dataset').json()['schema']['Tarih']=='Date'
    assert client.get('/pivot').json()['meta']['matched_rows']==2000
    assert client.get('/docs').status_code==200
    assert '/pivot' in client.get('/openapi.json').json()['paths']

def test_reproducibility():
    assert generate_sales(100,42).equals(generate_sales(100,42))
    assert not generate_sales(100,42).equals(generate_sales(100,43))

def test_million_row_api():
    with TestClient(create_app()) as c:
        response=c.get('/pivot')
        assert response.status_code==200
        r=response.json()
        assert r['meta']['source_rows']==r['meta']['matched_rows']==1_000_000
        assert r['meta']['total_sales']==int(c.app.state.sales['Satis_Adedi'].sum())
        assert len(r['data'])==7 and len(r['columns'])==6
