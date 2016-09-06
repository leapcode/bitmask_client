// bitmask.js
// Copyright (C) 2016 LEAP
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

/**
 * bitmask object
 *
 * Contains all the bitmask API mapped by sections
 * - user. User management like login, creation, ...
 * - mail. Email service control.
 * - keys. Keyring operations.
 * - events. For registering to events.
 *
 * Every function returns a Promise that will be triggered once the request is
 * finished or will fail if there was any error. Errors are always user readable
 * strings.
 */

import Promise from 'promise'

var bitmask = function(){
    var event_handlers = {};

    function call(command) {
        var url = '/API/' + command.slice(0, 2).join('/');
        var data = JSON.stringify(command.slice(2));

        return new Promise(function(resolve, reject) {
            var req = new XMLHttpRequest();
            req.open('POST', url);

            req.onload = function() {
                if (req.status == 200) {
                    parseResponse(req.response, resolve, reject);
                }
                else {
                    reject(Error(req.statusText));
                }
            };

            req.onerror = function() {
                reject(Error("Network Error"));
            };

            req.send(data);
        });
    };

    function parseResponse(raw_response, resolve, reject) {
        var response = JSON.parse(raw_response);
        if (response.error === null) {
            resolve(response.result);
        } else {
            reject(response.error);
        }
    };

    function event_polling() {
        call(['events', 'poll']).then(function(response) {
            if (response !== null) {
                evnt = response[0];
                content = response[1];
                if (evnt in event_handlers) {
                    event_handlers[evnt](evnt, content);
                }
            }
            event_polling();
        }, function(error) {
            setTimeout(event_polling, 5000);
        });
    };
    event_polling();

    function private_str(priv) {
        if (priv) {
            return 'private'
        }
        return 'public'
    };

    return {
        /**
         * uids are of the form user@provider.net
         */
        user: {
            /**
             * Check which user is active
             *
             * @return {Promise<string>} The uid of the active user
             */
            active: function() {
                return call(['user', 'active']);
            },

            /**
             * Register a new user
             *
             * @param {string} uid The uid to be created
             * @param {string} password The user password
             */
            create: function(uid, password) {
                return call(['user', 'create', uid, password]);
            },

            /**
             * Login
             *
             * @param {string} uid The uid to log in
             * @param {string} password The user password
             */
            auth: function(uid, password) {
                return call(['user', 'authenticate', uid, password]);
            },

            /**
             * Logout
             *
             * @param {string} uid The uid to log out.
             *                     If no uid is provided the active user will be used
             */
            logout: function(uid) {
                if (typeof uid !== 'string') {
                    uid = "";
                }
                return call(['user', 'logout', uid]);
            }
        },

        mail: {
            /**
             * Check the status of the email service
             *
             * @return {Promise<string>} User readable status
             */
            status: function() {
                return call(['mail', 'status']);
            },

            /**
             * Get the token of the active user.
             *
             * This token is used as password to authenticate in the IMAP and SMTP services.
             *
             * @return {Promise<string>} The token
             */
            get_token: function() {
                return call(['mail', 'get-token']);
            }
        },

        /**
         * A KeyObject have the following attributes:
         *   - address {string} the email address for wich this key is active
         *   - fingerprint {string} the fingerprint of the key
         *   - length {number} the size of the key bits
         *   - private {bool} if the key is private
         *   - uids {[string]} the uids in the key
         *   - key_data {string} the key content
         *   - validation {string} the validation level which this key was found
         *   - expiry_date {string} date when the key expires
         *   - refreshed_at {string} date of the last refresh of the key
         *   - audited_at {string} date of the last audit (unused for now)
         *   - sign_used {bool} if has being used to checking signatures
         *   - enc_used {bool} if has being used to encrypt
         */
        keys: {
            /**
             * List all the keys in the keyring
             *
             * @param {boolean} priv Should list private keys?
             *                       If it's not provided the public ones will be listed.
             *
             * @return {Promise<[KeyObject]>} List of keys in the keyring
             */
            list: function(priv) {
                return call(['keys', 'list', private_str(priv)]);
            },

            /**
             * Export key
             *
             * @param {string} address The email address of the key
             * @param {boolean} priv Should get the private key?
             *                       If it's not provided the public one will be fetched.
             *
             * @return {Promise<KeyObject>} The key
             */
            exprt: function(address, priv) {
                return call(['keys', 'export', address, private_str(priv)]);
            },

            /**
             * Insert key
             *
             * @param {string} address The email address of the key
             * @param {string} rawkey The key material
             * @param {string} validation The validation level of the key
             *                            If it's not provided 'Fingerprint' level will be used.
             *
             * @return {Promise<KeyObject>} The key
             */
            insert: function(address, rawkey, validation) {
                if (typeof validation !== 'string') {
                    validation = 'Fingerprint';
                }
                return call(['keys', 'insert', address, validation, rawkey]);
            },

            /**
             * Delete a key
             *
             * @param {string} address The email address of the key
             * @param {boolean} priv Should get the private key?
             *                       If it's not provided the public one will be deleted.
             *
             * @return {Promise<KeyObject>} The key
             */
            del: function(address, priv) {
                return call(['keys', 'delete', address, private_str(priv)]);
            }
        },

        events: {
            /**
             * Register func for an event
             *
             * @param {string} evnt The event to register
             * @param {function} func The function that will be called on each event.
             *                        It has to be like: function(event, content) {}
             *                        Where content will be a list of strings.
             */
            register: function(evnt, func) {
                event_handlers[evnt] = func;
                return call(['events', 'register', evnt])
            },

            /**
             * Unregister from an event
             *
             * @param {string} evnt The event to unregister
             */
            unregister: function(evnt) {
                delete event_handlers[evnt];
                return call(['events', 'unregister', evnt])
            }
        }
    };
}();

module.exports = bitmask