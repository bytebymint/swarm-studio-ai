import json
import threading
import zipfile
from pathlib import Path

import httpx
import pytest
from PIL import Image

from app.blueprint import DependencyGraph, build_blueprint
from app.config import Settings
from app.projects import ProjectStore
from app.reconstruction import reconstruct
from app.server import PreviewServer
from app.urls import normalize_url
from app.validation import compare_images


def test_urls():
    assert normalize_url('example.com') == 'https://example.com'
    assert normalize_url(' localhost:8000/a ') == 'http://localhost:8000/a'
    assert normalize_url('127.0.0.1:3000') == 'http://127.0.0.1:3000'
    for value in ['file:///C:/secret','javascript:alert(1)','https://me:password@example.com','https://x.test/?access_token=secret','https://example.com:bad','']:
        with pytest.raises(ValueError):normalize_url(value)


def test_graph_dependencies_failures_cancellation():
    tasks=[{'id':'a','dependencies':[]},{'id':'b','dependencies':['a']},{'id':'c','dependencies':['b']}]
    graph=DependencyGraph(tasks)
    assert graph.assign('Ada')['id']=='a'
    assert graph.assign('Ada') is None
    assert graph.assign('Grace') is None
    graph.finish('Ada')
    assert graph.assign('Grace')['id']=='b'
    graph.finish('Grace',False)
    assert graph.tasks['c']['status']=='blocked'
    assert not graph.complete
    graph=DependencyGraph(tasks)
    graph.assign('Ada');graph.cancel()
    assert graph.assign('Grace') is None
    assert not graph.owners
    assert DependencyGraph([]).complete
    with pytest.raises(ValueError):DependencyGraph([{'id':'a','dependencies':['a']}])
    with pytest.raises(ValueError):DependencyGraph([{'id':'a','dependencies':['missing']}])
