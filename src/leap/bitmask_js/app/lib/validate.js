// https://github.com/dropbox/zxcvbn

var DOMAIN_RE = /^((?:(?:(?:\w[\.\-\+]?)*)\w)+)((?:(?:(?:\w[\.\-\+]?){0,62})\w)+)\.(\w{2,6})$/
var USER_RE   = /^[a-z0-9_-]{1,200}$/
var USER_INT_RE = /^[\.@a-z0-9_-]*$/

//
// Validations returns an error message or false if no errors
//

class Validations {

  domain(input) {
    if (!input.match(DOMAIN_RE)) {
      return "Not a domain name"
    } else {
      return null
    }
  }

  usernameInteractive(input) {
    if (!input.match(USER_INT_RE)) {
      return "Username contains an invalid character"
    }
    return false
  }

  username(input) {
    if (!input.match(USER_INT_RE)) {
      return "Username contains an invalid character"
    }
    if (!input.match('@')) {
      return "Username must be in the form username@domain"
    }
    let parts      = input.split('@')
    let userpart   = parts[0]
    let domainpart = parts[1]
    if (!userpart.match(USER_RE)) {
      return "Username contains an invalid character"
    } else if (!domainpart.match(DOMAIN_RE)) {
      return "Username must include a valid domain name."
    }
    return false
  }

  passwordStrength(passwd) {
    if (typeof(zxcvbn) == 'function') {
      // zxcvbn performs very slow on long strings, so we cap
      // the calculation at 30 characters
      return zxcvbn(passwd.substring(0,30))
    } else {
      return null
    }
  }

  //
  // loads the zxcvbn library. because this library is big, we don't load it
  // every time, just when needed.
  //
  // this is the webpack way to do this:
  //
  //    require.ensure([], function () {
  //      var zxcvbn = require('zxcvbn');
  //    });
  //
  // that works, but requires that we also process the original coffeescript
  // source if we want to avoid warning messages.
  //
  loadPasswdLib(onload) {
    var id = "zxcvbn-script"
    if (!document.getElementById(id)) {
      var script = document.createElement('script')
      script.id = id
      script.onload = onload
      script.src = './js/zxcvbn.js'
      document.getElementsByTagName('script')[0].appendChild(script)
    }
  }
}

var Validate = new Validations()
export default Validate
