clean:
	-rm -f `find . -name "*~"`
	-rm -f `find . -name "*.pyc"`
	-rm -f `find . -name "*.class"`
	-rm -f `find . -name "*.bak"`

ChangeLog:
	cvs2cl
	cvs commit ChangeLog
	rm ChangeLog.bak
