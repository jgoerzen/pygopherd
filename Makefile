clean:
	-python2.2 setup.py clean --all
	-rm -f `find . -name "*~"`
	-rm -f `find . -name "*.pyc"`
	-rm -f `find . -name "*.pygc"`
	-rm -f `find . -name "*.class"`
	-rm -f `find . -name "*.bak"`
	-rm -f `find . -name ".cache*"`

changelog:
	cvs2cl
	cvs commit ChangeLog
	rm ChangeLog.bak
