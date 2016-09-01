//
// Color.hsv().css
//
// RGB values are 0..255
// HSV values are 0..1
//

function compose(value)
  return [
    Math.round(value * 255),
    Math.round(value * 255),
    Math.round(value * 255)
  }
}

class Color {

  constructor(r, g, b, a) {
    this.r = r
    this.g = g
    this.b = b
    this.a = a
  }

  //
  // alternate hsv factory
  //
  static hsv(h,s,v) {
    let out = null
    h = h % 360;
    s = Math.max(0, Math.min(1, s))
    v = Math.max(0, Math.min(1, v))

    if (s == 0) {
      let grey = Math.ceil(v*255)
      out = [grey, grey, grey]
    }

    let b = ((1 - s) * v);
    let vb = v - b;
    let hm = h % 60;
    switch((h/60)|0) {
      case 0:
        out = compose(v, vb * h / 60 + b, b); break
      case 1:
        out = compose(vb * (60 - hm) / 60 + b, v, b); break
      case 2:
        out = compose(b, v, vb * hm / 60 + b); break
      case 3:
        out = compose(b, vb * (60 - hm) / 60 + b, v); break
      case 4:
        out = compose(vb * hm / 60 + b, b, v); break
      case 5:
        out = compose(v, b, vb * (60 - hm) / 60 + b); break
    }

    return new Color(...out)
  }

  css() {
    return `rgba(${this.r}, ${this.g}, ${this.b}, ${this.a})`
  }
}

export default Color