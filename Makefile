clean:
	-rm -f `find . -name "*~"`
	-rm -f `find . -name "*.pyc"`
	-rm -f `find . -name "*.class"`

ChangeLog:
	cvs2cl
	cvs commit ChangeLog
