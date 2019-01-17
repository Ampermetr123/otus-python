import unittest
import sys
import json
import os
import log_analyzer as la
from os.path import join, exists
import time
import webbrowser


class LoadConfigTests(unittest.TestCase):
    """Load config tests (reload_config method)"""

    def test_empty_config(self):
        """Test default values are used when parameters not presented in config file"""
        sys.argv = sys.argv[:1]
        sys.argv.append('--config=./tests/empty_config.cfg')
        with open('./tests/empty_config.cfg', 'w') as f:
            json.dump({}, f)
        cfg = la.reload_config(la.get_config_filename(), la.config)
        self.assertDictEqual(cfg, la.config)
        os.remove('./tests/empty_config.cfg')

    def test_user_config(self):
        """Test correct loading parameters from config file"""
        with open('./tests/user_config.cfg', 'w', encoding='utf-8') as f:
            json.dump({"REPORT_SIZE": 20, "REPORT_DIR": "./reports"}, f)
        sys.argv = sys.argv[:1]
        sys.argv.append('--config=./tests/user_config.cfg')
        cfg = la.reload_config(la.get_config_filename(), la.config)
        self.assertEqual(cfg['REPORT_SIZE'], 20)
        self.assertEqual(cfg['REPORT_DIR'], './reports')
        self.assertEqual(cfg['LOG_DIR'], la.config['LOG_DIR'])
        os.remove('./tests/user_config.cfg')

    def test_wrong_config(self):
        """Test exception (program stops) on wrong config file"""
        sys.argv = sys.argv[:1]
        sys.argv.append('--config=test_file_not_exist')
        with self.assertRaises(Exception):
            cfg = la.reload_config(la.get_config_filename(), la.config)

        sys.argv = sys.argv[:1]
        sys.argv.append('--config=log_analyzer.py')
        with self.assertRaises(Exception):
            cfg = la.reload_config(la.get_config_filename(), la.config)


class FindLatestLogTests(unittest.TestCase):
    """Find accustomed log file to analyze tests (get_latest_logfile_info method)"""

    def test_empty_folder(self):
        """Test correct function return when empty folder"""
        file_info = la.get_latest_logfile_info('./tests/log_empty')
        self.assertIsNone(file_info.path)
        pass

    def test_no_correct_filename(self):
        """Test correct return when no valid files names in folder"""
        file_info = la.get_latest_logfile_info('./tests/log_no_file')
        self.assertIsNone(file_info.path)

    def test_latest_gz(self):
        """Test correct return latest gz-log file"""
        file_info = la.get_latest_logfile_info('./tests/log_gz')
        self.assertEqual(join('./tests/log_gz', 'nginx-access-ui.log-20190105.gz'), file_info.path)
        self.assertEqual('20190105', file_info.date.strftime('%Y%m%d'))

    def test_latest_plain(self):
        """Test correct return latest plain-log file"""
        file_info = la.get_latest_logfile_info('./tests/log_plain')
        self.assertEqual(join('./tests/log_plain', 'nginx-access-ui.log-20190103'), file_info.path)
        self.assertEqual('20190103', file_info.date.strftime('%Y%m%d'))


class AnalyzeTest(unittest.TestCase):
    """Tests analyze and report"""

    def test_analyze(self):
        """Check correct analyze test log file"""

        # file contains 6 correct requests. 2 url's are the same.
        file_info = la.get_latest_logfile_info('./tests/log_generate_report')
        data = la.analyse_log_file(file_info.path)

        sdb = sorted(data, key=lambda p: p['url'])
        self.assertEqual(5, len(sdb), msg='Test log file contains 5 corrected unique requests')
        self.assertEqual(sdb[0]['url'], '1_test_url', msg='Url check')
        self.assertEqual(sdb[0]['count'], 1, msg='Count check')
        self.assertAlmostEqual(sdb[0]['time_sum'], 0.5, delta=0.001, msg='Time_sum check')
        self.assertAlmostEqual(sdb[0]['time_avg'], 0.5, delta=0.001, msg='Time_avg_check')
        self.assertAlmostEqual(sdb[0]['count_perc'], 100 / 6, delta=0.001, msg='Count_perc check')
        self.assertAlmostEqual(sdb[0]['time_perc'], 0.5 * 100 / 3, delta=0.001, msg='Time_perc check')

        self.assertEqual(sdb[4]['url'], '5_double_url', msg='Url check')
        self.assertEqual(sdb[4]['count'], 2, msg='Count check')
        self.assertAlmostEqual(sdb[4]['count_perc'], 2 * 100 / 6, delta=0.001, msg='Count_perc check')
        self.assertAlmostEqual(sdb[4]['time_sum'], 0.5, delta=0.001, msg='Time_sum check')
        self.assertAlmostEqual(sdb[4]['time_avg'], 0.25, delta=0.001, msg='Time_avg_check')
        self.assertAlmostEqual(sdb[4]['time_perc'], 0.5 * 100 / 3, delta=0.001, msg='Time_perc check')

    def test_file_format_error(self):
        """Test error generated when most of lines couldn't be parsed"""
        file_info = la.get_latest_logfile_info('./tests/log_bad_format')
        with self.assertRaises(UserWarning):
            la.analyse_log_file(file_info.path, 40)

    def test_integral(self):
        """Ultimate integral test. It may takes several minutes. Check result in browser (10 rows)."""

        # print("\n"
        #       )
        sys.argv = sys.argv[:1]
        sys.argv.append('--config=tests/test_integral.cfg')
        logger_file = 'tests/log_integral/log_analyzer.log'
        output_file = 'tests/log_integral_report/report-2017-06-30.html'
        output_url = 'file:///' + os.path.abspath(output_file)

        if exists(output_file):
            os.remove(output_file)
        if exists(logger_file):
            os.remove(logger_file)

        # main will raises exception on errors
        try:
            la.main(la.config)
        except Exception as ex:
            self.fail("log_analyzer main() function failed with %s(%s)" % (type(ex).__name__, ex))

        self.assertTrue(exists(output_file), msg="Checks report file generated")
        self.assertTrue(exists(logger_file), msg="Checks logger file was created")

        # check do not process when report is already present
        start = time.time()
        try:
            la.main(la.config)
        except Exception as ex:
            self.fail("log_analyzer main() function failed with %s(%s)" % (type(ex).__name__, ex))
        timeout = time.time() - start
        self.assertTrue(timeout < 1, "If report is ready, program shouldn't parse log again")
        webbrowser.open(output_url, new=2)


if __name__ == '__main__':
    la_TestSuite = unittest.TestSuite()
    la_TestSuite.addTest(unittest.makeSuite(LoadConfigTests))
    la_TestSuite.addTest(unittest.makeSuite(FindLatestLogTests))
    la_TestSuite.addTest(unittest.makeSuite(AnalyzeTest))
    unittest.TextTestRunner(verbosity=3).run(la_TestSuite)
