import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# 测试必须隔离到临时目录，绝不能碰用户真实数据
_TMP = tempfile.mkdtemp(prefix="soulpet-test-")
os.environ["SOULPET_HOME"] = _TMP
os.environ["SOULPET_MASTER_KEY"] = "test-master-key"


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app) as c:
        yield c
