import os

def test_lisr_artifacts():
    assert os.path.exists("data/federal/mx-fed-lisr.xml")
    assert os.path.exists("engines/catala/lisr.catala_en")
