import unittest
import log_analyzer_tests as lt

la_TestSuite = unittest.TestSuite()

la_TestSuite.addTest(unittest.makeSuite(lt.LoadConfigTests))
la_TestSuite.addTest(unittest.makeSuite(lt.FindLatestLogTests))
la_TestSuite.addTest(unittest.makeSuite(lt.AnalyzeTest))

unittest.TextTestRunner(verbosity=3).run(la_TestSuite)
