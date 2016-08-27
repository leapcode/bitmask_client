//
// An account is an abstraction of a user and a provider.
// The user part is optional, so an Account might just represent a provider.
//

import bitmask from 'lib/bitmask'

export default class Account {

  constructor(address, props={}) {
    if (!address.match('@')) {
      this._address = '@' + address
    } else {
      this._address = address
    }
    this._authenticated = props.authenticated
  }

  //
  // currently, bitmask.js uses address for id, so we return address here too.
  // also, we don't know uuid until after authentication.
  //
  // TODO: change to uuid when possible.
  //
  get id() {
    return this._address
  }

  get domain() {
    return this._address.split('@')[1]
  }

  get address() {
    return this._address
  }

  get userpart() {
    return this._address.split('@')[0]
  }

  get authenticated() {
    return this._authenticated
  }

  //
  // returns a promise, fulfill is passed account object
  //
  login(password) {
    return bitmask.user.auth(this.address, password).then(
      response => {
        if (response.uuid) {
          this._uuid = response.uuid
          this._authenticated = true
        }
        return this
      }
    )
  }

  //
  // returns a promise, fulfill is passed account object
  //
  logout() {
    return bitmask.user.logout(this.id).then(
      response => {
        this._authenticated = false
        this._address = '@' + this.domain
        return this
      }
    )
  }

  //
  // returns a promise, fullfill is passed account object
  //
  static active() {
    return bitmask.user.active().then(
      response => {
        if (response.user == '<none>') {
          return null
        } else {
          return new Account(response.user, {authenticated: true})
        }
      }
    )
  }

}