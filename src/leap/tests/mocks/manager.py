from mock import Mock

from eip_client.vpnmanager import OpenVPNManager

vpn_commands = {
        'status': [
            'OpenVPN STATISTICS', 'Updated,Mon Jun 25 11:51:21 2012',
            'TUN/TAP read bytes,306170', 'TUN/TAP write bytes,872102',
            'TCP/UDP read bytes,986177', 'TCP/UDP write bytes,439329',
            'Auth read bytes,872102'],
        'state': ['1340616463,CONNECTED,SUCCESS,172.28.0.2,198.252.153.38'],
        # XXX add more tests
        }


def get_openvpn_manager_mocks():
    manager = OpenVPNManager()
    manager.status = Mock(return_value='\n'.join(vpn_commands['status']))
    manager.state = Mock(return_value=vpn_commands['state'][0])
    return manager
