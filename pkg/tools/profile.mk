do_cprofile:
	python -m cProfile -o bitmask.cprofile src/leap/bitmask/app.py --debug -N

view_cprofile:
	cprofilev bitmask.cprofile

mailprofile:
	gprof2dot -f pstats /tmp/leap_mail_profile.pstats -n 0.2 -e 0.2 | dot -Tpdf -o /tmp/leap_mail_profile.pdf

do_lineprof:
	LEAP_PROFILE_IMAPCMD=1 LEAP_MAIL_MANHOLE=1 kernprof.py -l src/leap/bitmask/app.py --debug

do_lineprof_offline:
	LEAP_PROFILE_IMAPCMD=1 LEAP_MAIL_MANHOLE=1 kernprof.py -l src/leap/bitmask/app.py --offline --debug -N

view_lineprof:
	@python -m line_profiler app.py.lprof | $(EDITOR) -

resource_graph:
	#./pkg/scripts/monitor_resource.zsh `ps aux | grep app.py | head -1 | awk '{print $$2}'` $(RESOURCE_TIME)
	./pkg/scripts/monitor_resource.zsh `pgrep bitmask` $(RESOURCE_TIME)
	display bitmask-resources.png

