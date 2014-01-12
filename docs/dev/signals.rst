Startup process
---------------

mainwindow._login -> backend.run_provider_setup_checks
[...provider bootstrap...]
self._provider_config_loaded
[...login...]
authentication_finished
_start_eip_bootstrap
_maybe_start_eip
_maybe_run_soledad_setup_checks
soledadbootstrapper
