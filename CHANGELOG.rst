.. :changelog::

History
-------

0.3.8 Dec 6 -- the "Three week child" release:
+++++++++++++++++++++++++++++++++++++++++++++++
- Make the preferences window selects the current selected provider in
  the login widget even if the user is not logged in. Closes #4490.
- Support non-ascii characters in a provider name. Closes #4952.
- Disable Turn On EIP in tray if the service is disabled. Closes #4630.
- Do not show the generic message "EIP has stopped" since it's
  redundant. Fixes #4632.
- Avoid attempt to install policykit file in debian package. Closes:
  #4404
- Properly close Soledad at quit time. Fixes #4504.
- Fix soledad bootstrap subtasks order. Closes #4537.
- Add --nobind as a VPN parameter to prevent binding on local
  addresses. Fixes #4543.
- Disable Turn On EIP until we have an usable provider. Closes #4523.
- Load provider if the wizard was rejected and the setup was
  completed.
- Disable Turn On EIP if the "Encrypted Internet" service is disabled.
  Closes #4555.
- If EIP service is disabled display 'Disabled' instead of 'You need
  to login to use Encrypted Internet'.
- Disable eip-config until we have configured the provider. Closes
  #4422.

0.3.7 Nov 15 -- the "The Big Lebowsky" release:
+++++++++++++++++++++++++++++++++++++++++++++++
- Use custom SysTray in order to display per-service tooltip easily.
  Closes #3998.
- Escape logs with html contents so they get displayed in plaintext
  on the log viewer. Closes #4146.
- Wizard now behaves correctly in provider selection after click
  'cancel' or 'back'. Closes #4148.
- Handle Timeout errors during register process. Closes #4358.
- Send user's key to nickserver whenever keymanager is
  initialized. Closes #4364.
- Password change dialog is now properly enabled. Closes #4449.
- Remember provider checks in wizard, do not re-run them if the user
  goes back and forth through the wizard. Closes #3814 and #3815.
- Improve compatibility with OSX Mavericks. Fixes #4379.
- Initialize mail service with the userid after login, to allow
  multiple accounts. Closes: #4394
- Give SMTP the current logged in userid. Related to #3952.
- Do not wait for initial soledad sync to complete to launch mail
  services. Closes: #4452
- Add hint to user about the duration of the key generation. Closes
  #3958.
- Add advanced key management feature. Closes #4448.
- Properly log EIP status changes.

0.3.6 Nov 1 -- the "bạn có thể đọc này?" release:
+++++++++++++++++++++++++++++++++++++++++++++++++

- Fix problem changing a non-ascii password. Closes #4003.
- Enable password change in the client only if it has started the
  correct services. Closes #4093.
- Select the current logged in provider in the preferences
  window. Closes #4117.
- Fix problem with non-ascii paths. Closes #4189.
- Capture soledad boostrap errors after latest soledad changes.
- Refactor keyring handling and make it properly save user and
  password. Fixes #4190.
- Properly stop the imap daemon at logout. Fixes #4199.
- Align left the speed and transferred displays for EIP. Fixes #4204.
- Remove autostart eip option from settings panel, rely on last used
  setting. Closes #4132.
- Add support for requests 1.1.0 (raring). Closes: #4308
- Refactor mail connections to use state machine. Closes: #4059
- Add a command to setup.py to freeze the versions reported under
  debian branches. Closes: #4315
- Use coloredlogs handler if present (for development, not a
  requirement).
- Hide the GUI for services that are not supported on the set of
  configured providers. Closes #4170.

0.3.5 Oct 18 -- the "I can stand on one foot" release:
++++++++++++++++++++++++++++++++++++++++++++++++++++++

- In case of Soledad failure, display to the user that there was a
  problem. Closes #4025.
- Widget squashing problem in wizard checking a new provider. Closes
  #4058.
- Remember last domain used to login. Closes #4116.
- Display first run wizard, regardless of pinned providers. Closes
  #4143.
- Show EIP status 'ON' in the systray tooltip when is
  connected. Related to #3998.
- Catch u1db errors during soledad initialization.
- Disable --danger flag on release versions. Closes #4124.
- Display mail status in the tray icon as an enabled item. Fixes
  #4036.
- Only show N unread Emails when N > 0. Fixes #4098.
- Hide login error message when the user interacts with the widgets
  to fix the potential problem. Fixes #4022.
- Add call to `make` to the bootstrap script.
- Improve GUI based on QA rounds. Fixes #4041 and #4042.
- Increase the amount of retries for the authentication request
  session. Fixes #4037.
- Rename EIP to Encrypted Internet in its preference panel. Fixes
  #4057.
- Disable stdout redirection on Windows for the time being since it
  breaks the bundle.
- Default UP_SCRIPT and DOWN_SCRIPT to None and only add that
  parameter to the vpn command if not None.
- Look for gpg on windows with the .exe extension.
- Change the Util menu to be named File in OSX. Fixes #4039.
- Show more context information in the logs. Closes #3923.
- Automate internationalization process, create project file
  dynamically on make. Closes #3925.
- Add support for running lxde polkit agent. Closes #4028.
- Added Vietnamese and English (United Kingdom) translations.
- Implements openvpn observer. Closes: #3901
- Reconnect EIP if network down. Closes #3790
- Reconnect if tls-restart. Closes: #3262

0.3.4 Oct 4 -- the "look at my new makeup" release:
+++++++++++++++++++++++++++++++++++++++++++++++++++

- Fixes a bug where you cannot login to a different provider once
  you logged in to another one. Fixes #3695.
- Resets the session for every login attempt. Related to #3695.
- Avoid error message if --version flag is used. Closes #3914.
- Fix a bug in which failing to authenticate properly left
  connection in an unconsistent state. Closes: #3926
- Avoids errors due to the EIP switch button and action being
  enabled when we do not have a configured provider. Closes: #3927
- Add more verbose error handling during key generation and syncing.
  Helps diagnose: #3985; Addresses in part: #3965
- Choose one gnupg binary path that is also not a symlink. Closes
  #3999.
- Refactor vpn launchers, reuse code, improve implementations,
  update documentation. Closes #2858.
- Add preferences option to enable/disable the automatic start of
  EIP and selection of the EIP provider to auto start. Closes #3631.
- Force cleanlooks style for kde only if the app is running from
  bundle. Closes #3981.
- Add a dropdown for known providers in the wizard. Closes #3995.
- Separate pinned providers from user configures ones. Closes #3996.
- Improve error handling during soledad bootstrap. Closes: #3965.
  Affects: #3619, #3867, #3966
- Implement new UI design. Closes #3973.
- Make the initial provider cert verifications against our modified
  CA-bundle (includes ca-cert certificates, for now). Closes: #3850
- Use token header for authenticated requests. Closes #3910.
- Do not distinguish between different possible authentication
  errors. Fixes #3859.
- Do not start Soledad if Mail is not enabled. Fixes #3989.
- Allow window minization on OSX. Fixes #3932.
- Properly stop the smtp daemon. Fixes #3873.

0.3.3 Sep 20 -- "the calm after the tempest" release:
+++++++++++++++++++++++++++++++++++++++++++++++++++++

- Remove execution bits in text files in bundle. Closes #3617.
- Use generic bad username/password message instead of specific ones when
  the user uses incorrect data during login. Closes #3656.
- Fix LoggerWindow saving more than one line return per line in the logs
  file. Closes #3714.
- Fix keyring imports so we do not get import errors. Closes: #3759
- Catch logout problem, display a user message and allow log back in after a
  successful logout if there was a logout error before. Closes #3774.
- Fix path prefix helper for the bundle and add regresion tests. Closes #3778.
- Prevent dialogs closing the app when it has been minimized to the tray. Closes #3791.
- Do not try to install resolv-update globally. Closes: #3803
- Inconsistent hide/show main window from tray action. Closes #3821.
- Allow SMTP to start even when provider does not offer EIP. Closes: #3847
- Fix username case problem at register/login. Closes #3857.
- Catch IndexError on `first` utility.
- Update git repo name in docs. Closes: #3417
- Move STANDALONE flag to a module and unify get_path_prefix queries.
  Closes #3636.
- Display the Encrypted Internet and Encrypted Email status in the systray
  tooltip. Closes #3758.
- Tasktray menu changes, closes #3792.
- Remove the provider domain item (e.g. bitmask.net).
- Rename the EIP status menu items to be more descriptive.
- Change the EIP status menu items from disabled menu items
  to submenus with children.
- Move the EIP action menu items under the EIP status submenu tree.
- Adds ``--version`` flag. Closes: #3816
- Refactors EIPConnection to use LEAPConnection state machine. Closes: #3900
- Include resource files and ui in the distrubution tarball. Closes: #3825

0.3.2 Sep 6 -- the "no crashes or anything" release:
++++++++++++++++++++++++++++++++++++++++++++++++++++

- Fix up script in non-bundle linuces. Closes: #3450
- Logout stops imap and smtp services. Closes: #3553
- Properly daemonize polkit-gnome-authentication-agent. Closes: #3554
- Set appropiate error on login cancel. Closes #3582.
- Fix gateway selection problem. Closes 3595.
- Fix typo in wizard: stablish -> establish. Closes #3615.
- Display Encrypted Mail instead of mx in wizard. Closes #3657.
- Fix save logs to file dialog freezing. Closes #3675.
- Complain if setup.py is run with python3. Closes: #3711
- Enable preferences option in systray. Closes #3717.
- Make soledad emit failed signal for all kinds of socket error.
- Allow to selectively silence logs from different leap components. Closes: #3504
- Add option to select gateway manually in the preferences panel. Closes #3505.
- Add preferences option to select the enabled services of a provider. Closes #3534.
- Refactor basic password checks. Closes #3552.
- Use dirspec instead of plain xdg. Closes #3574.
- Remove last page from wizard. Closes #3616.
- Display encrypted mail status in the tray. Closes #3659.

0.3.1 Aug 23:
+++++++++++++

- Replace wizard images with the rainbow mask. Closes #3425.
- Update leap.common minimum version needed.
- Set the standalone flag before it's being used. Fixes #3426.
- Stop the twisted reactor adding the stop call to the call chain
  instead of stopping it directly. Fixes #3406.
- Allow soledad initialization to retry if it times out. Closes:
  #3413
- Activate window when setting it visible. Also display Hide/Show
  message in the tray icon taking into account the window
  activation. Fixes #3433.
- Do not start IMAP daemon if mail was not selected among the
  services. Fixes #3435.
- Reword RECONNECTING state of openvpn. Fixes #3429.
- Improve OpenVPN detection by searching for a specific leap-only
  string in the command line. This makes it possible to run other
  VPN instances while also using EIP. Fixes #3268 and #3364.
- OSX: Check for the tun.kext existence in /Library/Extensions
  instead of /System/Library/Extensions. Fixes #3271.
- Use DELETE /1/logout to properly logout. Fixes #3510.
- Make the poll interval bigger to improve openvpn's internal
  behavior. If it gets queried too many times per second, it's
  behavior won't be good. Fixes #3430.
- Transforms usernames to lower case before they are used in the
  registration and authentication. Closes #3541.
- Add filter option to the logger window. Closes #3407.
- Add a preference panel that lets you change your password. Closes
  #3500 #2798 #3533.
- Move all client code into its own namespace
  (leap.bitmask). Closes: #2959
- Make mail fetch interval in imap service configurable via
  environment variable. Closes: #3409
- Update to new soledad package scheme (common, client and
  server). Closes #3487.
- Fetch incoming mail when mail client logs in. Closes: #3525
- Add first draft of the UI for Encrypted Mail. Closes #3499.

0.3.0 Aug 9:
++++++++++++

- Add missing scripts does not stop if a command fails, also warns
  the user if there was an error. Closes #3294.
- Replace 'Sign Out' with 'Log Out' and 'User' with
  'Username'. Closes #3319.
- Verify cacert existence before using it. Closes bug #3362.
- Properly handle login failures. Closes bug #3401.
- Bugfix, avoid getting negative rates. Closes #3274.
- Raise window when setting it as visible. Fixes #3374
- Fail gracefully when the events port 8090 is in use by something
  else. Fixes #3276.
- Validate the username in the login form against the same regexp as
  the wizard registration form. Fixes #3214.
- Update text from the tray menu based on the visibility of the
  window. Fixes #3400.
- Add check for outdated polkit file. Closes #3209.
- Add support for multiple schemas so we can support multiples api
  versions. Closes #3310.
- Rebrand the client to be named Bitmask. Feature #3313.
- Add cancel button to login. Closes #3318.
- Add multiple schema support for SMTP. Closes #3403.
- Add multiple schema support for Soledad. Closes #3404.
- Update Transifex project name and translators'
  documentation. Closes #3418.
- Add check for tuntap kext before launching openvpn. Closes: #2906
- Accept flag for changing openvpn verbosity in logs. Closes: #3305
- Add imap service to the client. Closes: #2579
- Add pyside-uic support inside the virtualenv. This way it won't
  fail to 'make' if the virtualenv is activated. Closes #3411.
- Reintegrate SMTP relay module. Closes #3375
- Reintegrate Soledad into the client. Closes #3307.
- Support bundled gpg. Related to #3397.
- Set the default port for SMTP to be 2013.
- Display a more generic error message in the main window, and leave
  the detailed one for the log. Closes #3373.

0.2.4 Jul 26:
+++++++++++++

- Use the provider CA cert for every request once we have it
  bootstrapped (TOFU). Closes #3227.
- Make calls to leap.common.events asynchronous. Closes #2937.
- Always logout when closing the app if the user previously signed
  in. Fixes #3245.
- Make sure the domain field in provider.json is escaped to avoid
  potential problems. Fixes #3244.
- Fix incorrect handling of locks in Windows so that stalled locks
  do not avoid raising the first instance of the app. Closes: #2910
- Use traffic rates instead of totals. Closes #2913
- Allow to alternate between rates and total throughput for the
  virtual interface. Closes: #3232
- Reset rates/totals when terminating connection. Closes #3249
- Fix a bug in the displayed magnitude for the up/down traffic rates
  and totals.
- Force Cleanlooks style if we are running in a KDE environment, so
  that it doesn't load potentially incompatible Qt libs. Fixes
  #3194.
- Wrap long login status messages to 40 characters. Fixes #3124
- Workaround a segmentation fault when emitting a signal with its
  last parameter being None. Fixes #3083.
- Added IS_RELEASE_VERSION flag that allows us to use code only in
  develop versions. Closes #3224.
- Try to terminate already running openvpn instances. Closes #2916
- Linux: Dynamically generate policy file for polkit. Closes #3208
- Workaround some OpenVPN problems with priviledge dropping and
  routing. Fixes #3178 #3135 #3207 #3203

0.2.3 Jul 12:
+++++++++++++

- Adapt code to Soledad 0.2.1 api.
- Fix Main Window briefly display before the wizard on first
  start. Closes Bug #2954.
- Bugfix: Remember should not be automatically set to
  checked. Closes #2955.
- Bugfix: reload config if switching to a different provider. Closes
  #3067.
- Bugfix: logger window's toggle button reflects window
  state. Closes #3152.
- Set timeout for requests to 10 seconds globally, configurable from
  leap.util.constants. Fixes #2878.
- Bugfix: display error message on registration problem. Closes
  #3039.
- Make wizard use the main event loop, ensuring clean termination.
- Use cocoasudo for installing missing updown scripts.
- Bugfix: Systray Turn ON action fails because is not correctly
  enabled/disabled. Closes #3125.
- Bugfix: wrong systray icon on startup. Closes #3147.
- Bugfix: parse line return in the logger window. Closes #3151.
- Do not log user data on registration. Fixes #3168.
- Add --log-append eip.log to windows EIP launcher options to save
  the logs in case of any problems. Fixes #2054.
- OSX: Make the install_path relative to the launcher path instead
  -f absolute.
- OSX: Fix icon display in cocoasudo.
- OSX: Raise window when showing if running on OSX.
- Bugfix: EIP status button moved to status panel.
- Check if there is no gateway to use and display correct
  message. Close #2921.
- Reorder tray icons according new design. Closes #2919.
- Redirect stdout/stderr and twisted log to the logger. Closes
  #3134.
- Improve LoggerWindow colors for easier debugging.
- Move the key manager to its own repository/package.

0.2.2 Jun 28:
+++++++++++++

- Add support for the kde polkit daemon
- Handle 'Incorrect Password' exception (keyring)
- Select the configured domain in the providers combo box. Closes
  #2693.
- Remember provider along with the username and password. Closes
  #2755.
- Close the app on rejected wizard. Closes bug #2905.
- Only use the Keyring when it's using a known good backend. Closes
  #2960
- Update implementation and semantics of the supported and available
  services by a provider. Closes bug #3032.
- Only show the question mark for a check being done if the previous
  -ne passed. Fixes #2569.
- Fix main client window not restoring after minimized into
  systray. Closes #2574
- Set EIP different status icons depending on OS. Closes #2643.
- Reimplement openvpn invocation to use twisted ProcessProtocol
- Add runtime requirements checker, verifies that the requirements
  are installed and in its correct versions. Closes #2563
- Add centraliced logging facility, log history in a window. Closes
  #2566
- Improve wizard, hide registration widgets (labels, inputs, button)
  and only display a message. Closes #2694
- Clarify labels through the app (use of EIP)
- Check if the provider api version is supported. Closes feature
  #2774.
- Autoselect VPN gateway based on timezone. Closes #2790.
- Disable vpn disconnect on logout. Closes #2795.
- Improve gateway selector based on timezone. It allows to use
  multiple gateways in openvpn for redundancy. Closes #2894.
- Use cocoasudo in place of osascript for osx privilege escalation
  during openvpn launch.
- Clicking in the tray icon will always show the context menu
  instead of activating the window under certain
  circumstances. Closes #2788
- Autostart EIP whenever possible. Closes #2815
- Update test suite, run_scripts and requirements to run smoothly
  with buildbot.
- Add a copy of the processed requirements to util/
- Display the default provider configured in the systray menu. Close
  #2813
- Make the login steps be a chain of defers in order to be able to
  have more cancel points for the whole procedure. Closes #2571
- Linux: check for up/down scripts and policy files and ask user for
  permission to install them in a root-writeable location. Used from
  within bundle or for broken installations.
- Integrate SMTP-Relay into the client.
- Integrate Soledad and KeyManager.
- Move the KeyManager from leap.common to leap-client.
- Only use one systray icon, repesenting the status for EIP. Closes
  #2762
- Properly set the binary manifest to the windows openvpn
  binary. Closes #203
- OSX: Add dialog with suggestion to install up/down scripts if
  these not found. Closes: #1264, #2759, #2249
- Workaround for PySide breaking with multiple inheritance. Closes
  #2827
- Refactor login to its own widget and remove Utils menu. Closes
  #2789
- Refactor the status bits out of the MainWindow to its own
  StatusPanelWidget. Closes #2792
- Save the default provider to be used for autostart EIP as
  DefaultProvider in leap.conf. Closes #2793
- Cleanly terminate openvpn process, sending SIGTERM and SIGKILL
  after a while. Closes #2753
- Use twisted's deferToThread and Deferreds to handle parallel tasks
- Use a qt4 reactor for twisted, for launching leap twisted
  services.

0.2.1 May 15:
+++++++++++++

- Rewrite most of the client based on the insight gained so far.
- Deselecting the remember checkbox makes the app not populate
  user/password values on the login widget. Closes #2059
- Rewording of setup steps in wizard, to make them more meaningful
  to the non-technical user. Closes #2061
- Fix typo in wizard.
- Fix multiple drawing of services if going back.
- Make registration errors show in red.
- Add a warning if EIP service needs admin password. Addresses part
  -f #2062
- Make traffic indicators display fixed precision. Closes #2114
- Do not hide the application if the user right clicked the system
  tray icon.
- Sanitize network-fetched content that is used to build openvpn
  command.
- Avoids multiple instances of leap-client. Each new one just raises
  the existing instance and quits.
- Use dark eip icons os osx. Closes #2130
- Moves BaseConfig to leap.common.config. Closes #2164
- Add handling for ASSIGN_IP state from OpenVPN in the mainwindow.
- Emit events notifying of the session_id and uid after
  authentication so other services can make use of it. Closes #1957
- Working packaging workflow with rewritten client, using
  pyinstaller and platypus.
- Remove network checks temporarily until we find a good way of
  doing it, and a good way to deal with them.
- Saves the token to allow token authenticated queries.
- Turn "leap" into namespace package, move common files to
  leap_common package that can be shared by other LEAP projects.
- Support standalone configurations for distribution in thumbdrives
  and the like.
- Add support for requests < 1.0.0
- Tests infrastructure, and tests for crypto/srpauth and crypto/srpregister.
- Documentation updated for 0.2.1 release.
- Docstrings style changed to fit sphinx autodoc format.
- Add a simple UI to notify of pending updates.
- Add Windows support.
- Try to install TAP driver on Windows if no tap device is preset.
