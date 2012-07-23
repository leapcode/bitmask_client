fakeoutput = """
mullvad Sun Jun 17 14:34:57 2012 OpenVPN 2.2.1 i486-linux-gnu [SSL] [LZO2] [EPOLL] [PKCS11] [eurephia] [MH] [PF_INET6] [IPv6 payload 20110424-2 (2.2RC2)] built
 on Mar 23 2012
Sun Jun 17 14:34:57 2012 MANAGEMENT: TCP Socket listening on [AF_INET]127.0.0.1:7505
Sun Jun 17 14:34:57 2012 NOTE: the current --script-security setting may allow this configuration to call user-defined scripts
Sun Jun 17 14:34:57 2012 WARNING: file 'ssl/1021380964266.key' is group or others accessible
Sun Jun 17 14:34:57 2012 LZO compression initialized
Sun Jun 17 14:34:57 2012 Control Channel MTU parms [ L:1542 D:138 EF:38 EB:0 ET:0 EL:0 ]
Sun Jun 17 14:34:57 2012 Socket Buffers: R=[163840->131072] S=[163840->131072]
Sun Jun 17 14:34:57 2012 Data Channel MTU parms [ L:1542 D:1450 EF:42 EB:135 ET:0 EL:0 AF:3/1 ]
Sun Jun 17 14:34:57 2012 Local Options hash (VER=V4): '41690919'
Sun Jun 17 14:34:57 2012 Expected Remote Options hash (VER=V4): '530fdded'
Sun Jun 17 14:34:57 2012 UDPv4 link local: [undef]
Sun Jun 17 14:34:57 2012 UDPv4 link remote: [AF_INET]46.21.99.25:1197
Sun Jun 17 14:34:57 2012 TLS: Initial packet from [AF_INET]46.21.99.25:1197, sid=63c29ace 1d3060d0
Sun Jun 17 14:34:58 2012 VERIFY OK: depth=2, /C=NA/ST=None/L=None/O=Mullvad/CN=Mullvad_CA/emailAddress=info@mullvad.net
Sun Jun 17 14:34:58 2012 VERIFY OK: depth=1, /C=NA/ST=None/L=None/O=Mullvad/CN=master.mullvad.net/emailAddress=info@mullvad.net
Sun Jun 17 14:34:58 2012 Validating certificate key usage
Sun Jun 17 14:34:58 2012 ++ Certificate has key usage  00a0, expects 00a0
Sun Jun 17 14:34:58 2012 VERIFY KU OK
Sun Jun 17 14:34:58 2012 Validating certificate extended key usage
Sun Jun 17 14:34:58 2012 ++ Certificate has EKU (str) TLS Web Server Authentication, expects TLS Web Server Authentication
Sun Jun 17 14:34:58 2012 VERIFY EKU OK
Sun Jun 17 14:34:58 2012 VERIFY OK: depth=0, /C=NA/ST=None/L=None/O=Mullvad/CN=se2.mullvad.net/emailAddress=info@mullvad.net
Sun Jun 17 14:34:59 2012 Data Channel Encrypt: Cipher 'BF-CBC' initialized with 128 bit key
Sun Jun 17 14:34:59 2012 Data Channel Encrypt: Using 160 bit message hash 'SHA1' for HMAC authentication
Sun Jun 17 14:34:59 2012 Data Channel Decrypt: Cipher 'BF-CBC' initialized with 128 bit key
Sun Jun 17 14:34:59 2012 Data Channel Decrypt: Using 160 bit message hash 'SHA1' for HMAC authentication
Sun Jun 17 14:34:59 2012 Control Channel: TLSv1, cipher TLSv1/SSLv3 DHE-RSA-AES256-SHA, 2048 bit RSA
Sun Jun 17 14:34:59 2012 [se2.mullvad.net] Peer Connection Initiated with [AF_INET]46.21.99.25:1197
Sun Jun 17 14:35:01 2012 SENT CONTROL [se2.mullvad.net]: 'PUSH_REQUEST' (status=1)
Sun Jun 17 14:35:02 2012 PUSH: Received control message: 'PUSH_REPLY,redirect-gateway def1 bypass-dhcp,dhcp-option DNS 10.11.0.1,route 10.11.0.1,topology net30,ifconfig 10.11.0.202 10.11.0.201'
Sun Jun 17 14:35:02 2012 OPTIONS IMPORT: --ifconfig/up options modified
Sun Jun 17 14:35:02 2012 OPTIONS IMPORT: route options modified
Sun Jun 17 14:35:02 2012 OPTIONS IMPORT: --ip-win32 and/or --dhcp-option options modified
Sun Jun 17 14:35:02 2012 ROUTE default_gateway=192.168.0.1
Sun Jun 17 14:35:02 2012 TUN/TAP device tun0 opened
Sun Jun 17 14:35:02 2012 TUN/TAP TX queue length set to 100
Sun Jun 17 14:35:02 2012 do_ifconfig, tt->ipv6=0, tt->did_ifconfig_ipv6_setup=0
Sun Jun 17 14:35:02 2012 /sbin/ifconfig tun0 10.11.0.202 pointopoint 10.11.0.201 mtu 1500
Sun Jun 17 14:35:02 2012 /etc/openvpn/update-resolv-conf tun0 1500 1542 10.11.0.202 10.11.0.201 init
dhcp-option DNS 10.11.0.1
Sun Jun 17 14:35:05 2012 /sbin/route add -net 46.21.99.25 netmask 255.255.255.255 gw 192.168.0.1
Sun Jun 17 14:35:05 2012 /sbin/route add -net 0.0.0.0 netmask 128.0.0.0 gw 10.11.0.201
Sun Jun 17 14:35:05 2012 /sbin/route add -net 128.0.0.0 netmask 128.0.0.0 gw 10.11.0.201
Sun Jun 17 14:35:05 2012 /sbin/route add -net 10.11.0.1 netmask 255.255.255.255 gw 10.11.0.201
Sun Jun 17 14:35:05 2012 Initialization Sequence Completed
Sun Jun 17 14:34:57 2012 MANAGEMENT: TCP Socket listening on [AF_INET]127.0.0.1:7505
"""

import time
import sys


def write_output():
    for line in fakeoutput.split('\n'):
        sys.stdout.write(line + '\n')
        sys.stdout.flush()
        #print(line)
        time.sleep(0.1)

if __name__ == "__main__":
    write_output()
