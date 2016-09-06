//
// A proxy of an account, but with a different ID. For testing.
//

import bitmask from 'lib/bitmask'

export default class DummyAccount {

  constructor(account) {
    this.account = account
  }

  get id() {
    return 'dummy--' + this.account.address
  }

  get domain() {return this.account.domain}
  get address() {return this.account.address}
  get userpart() {return this.account.userpart}
  get authenticated() {return this.account.authenticated}
  get hasEmail() {return this.account.hasEmail}
  login(password) {return this.account.login(password)}

  logout() {
    return bitmask.user.logout(this.address).then(
      response => {
        this._authenticated = false
        this._address = '@' + this.domain
        return this
      }
    )
  }
}
