clean:
	-rm -f `find . -name "*~"`
	-rm -f `find . -name "*.pyc"`
	-rm -f `find . -name "*.class"`
	-rm -f `find . -name "*.bak"`
	-python2.2 setup.py clean --all

changelog:
	cvs2cl
	cvs commit ChangeLog
	rm ChangeLog.bak
