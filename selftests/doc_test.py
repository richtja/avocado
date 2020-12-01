import os
import re
import unittest

from avocado.utils import process

from . import BASEDIR


class DocTest(unittest.TestCase):

    def test_doc(self):
        for entry in os.scandir(os.path.join(BASEDIR, "examples", "doc")):
            if entry.is_file():
                with open(entry.path) as file:
                    expected_status = int(re.sub('[^0-9]+', '',
                                                 file.readlines()[1]))
                result = process.run(entry.path, ignore_status=True)
                self.assertEqual(expected_status, result.exit_status,
                                 "The doc_test %s fail" % entry.path)
