from flask import Flask
from flask import render_template
from flask import request
import netinterfaces
import os.path
import os
app = Flask(__name__)


@app.route('/')
def principal():
    list_interfaces = app.network_interface.get_real_list_interfaces()
    for x in app.network_interface.get_list_interfaces():
        if not x in list_interfaces:
            list_interfaces.append(x)
    list_interfaces.remove('lo')
    total = {}
    for x in list_interfaces:
        total[x] = parser_config(x)
    return render_template('main.html', list_interfaces=list_interfaces, serialized_interfaces=total)

@app.route('/reboot')
def reboot():
    os.system(local_config.REBOOT_INTERFACES)


@app.route('/update_info', methods=['POST'])
def update_info():
    interface = str(request.form['interface'])
    auto_start = True if 'auto-start' in request.form else False
    method = str(request.form['method'])
    dns = str(request.form['dns'].strip()).split('\n')
    ip = str(request.form["ip"].strip())
    netmask = str(request.form["mask"].strip())
    gateway = str(request.form["gateway"].strip())

    action = request.form["action"]
    if action == 'Save':
        if interface in list(app.network_interface.interface_mapping.keys()):
            app.network_interface.auto_toggle(interface, auto_start)
            if method == 'dhcp':
                app.network_interface.change_to_dhcp(interface)
            elif method == 'static':
                options = {'address': ip, 'netmask': netmask}
                if gateway != "":
                    options['gateway'] = gateway
                else:
                    #check if  needed remove gateway
                    for x in app.network_interface.interface_mapping[interface]:
                        if hasattr(x,'check_option'):
                            if x.check_option('gateway',True):
                                x.remove_option('gateway',True)
                app.network_interface.change_to_static(interface, options)
        else:
            if auto_start:
                new_stanza = netinterfaces.StanzaAuto([interface])
                app.network_interface.insert_stanza(new_stanza)
            new_stanza = netinterfaces.StanzaIface([interface], "inet " + method)
            if method != 'dhcp':
                new_stanza.set_option(str("address " + ip), unique=True)
                new_stanza.set_option(str("netmask " + netmask), unique=True)
                if gateway != "":
                    new_stanza.set_option(str("gateway " + gateway), unique=True)
            app.network_interface.insert_stanza(new_stanza)
        app.network_interface.update_dns(interface, dns)

    elif action == 'Delete':
        app.network_interface.delete_all_interface(interface)
        pass
    app.network_interface.write_file(local_config.OUTPUT_INTERFACE)
    return render_template('update.html',interfaces=app.network_interface.print_file())


def read_file(path_file):
    if os.path.exists(path_file):
        app.network_interface.load(path_file)
        return True
    else:
        return False


def parser_config(interface):
    result = {'auto': False}
    if interface in app.network_interface.interface_mapping:
        for stanza in app.network_interface.interface_mapping[interface]:
            if isinstance(stanza, netinterfaces.StanzaAuto):
                result['auto'] = True
            if isinstance(stanza, netinterfaces.StanzaIface):
                result['family'] = stanza.family
                result['method'] = stanza.method
                for option in stanza.options:
                    try:
                        key, value = option[:option.find(' ')], option[option.find(' ') + 1:]
                    except:
                        key = option
                    if key in result:
                        result[key].append(value)
                    else:
                        result[key] = [value]
    return result


import local_config
app.debug = local_config.DEBUG
app.network_interface = netinterfaces.InterfacesParser(local_config.LOG_PATH)
read_file(local_config.INPUT_INTERFACES)


if __name__ == '__main__':
    
    import local_config
    app.debug = local_config.DEBUG
    app.network_interface = netinterfaces.InterfacesParser(
        local_config.LOG_PATH)
    read_file(local_config.INPUT_INTERFACES)
    app.run(host=local_config.HOST, port=local_config.PORT)
