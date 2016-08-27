/*
 * A simple animated splash screen
 */

import React from 'react'
import * as COLOR from '../lib/colors'

const colorList = [
  COLOR.red200, COLOR.pink200, COLOR.purple200, COLOR.deepPurple200,
  COLOR.indigo200, COLOR.blue200, COLOR.lightBlue200, COLOR.cyan200,
  COLOR.teal200, COLOR.green200, COLOR.lightGreen200, COLOR.lime200,
  COLOR.yellow200, COLOR.amber200, COLOR.orange200, COLOR.deepOrange200
]

export default class Splash extends React.Component {

  static get defaultProps() {return{
    speed: "fast",
    mask: true,
    onClick: null
  }}

  constructor(props) {
    super(props)
    this.counter = 0
    this.interval = null
    this.ctx = null
    this.stepAngle = 0
    this.resize = this.resize.bind(this)
    this.click  = this.click.bind(this)
    if (this.props.speed == "fast") {
      this.fps = 30
      this.stepAngle = 0.005
    } else {
      this.fps = 30
      this.stepAngle = 0.0005
    }
  }

  componentDidMount() {
    this.interval = setInterval(this.tick.bind(this), 1000/this.fps)
    this.canvas   = this.refs.canvas
    this.ctx      = this.canvas.getContext('2d')
    window.addEventListener('resize', this.resize)
  }

  componentWillUnmount() {
    clearInterval(this.interval)
    window.removeEventListener('resize', this.resize)
  }

  click() {
    if (this.props.onClick) {
      this.props.onClick()
    }
  }

  tick() {
    this.counter++
    this.updateCanvas()
  }

  resize() {
    this.canvas.width = window.innerWidth
    this.canvas.height = window.innerHeight
    this.updateCanvas()
  }

  updateCanvas() {
    const arcCount = 16
    const arcAngle = 1 / arcCount
    const x = this.canvas.width / 2
    const y = this.canvas.height / 2
    const radius = screen.height + screen.width

    for (let i = 0; i < arcCount; i++) {
      let startAngle = Math.PI * 2 * i/arcCount + this.stepAngle*this.counter
      let endAngle   = Math.PI * 2 * (i+1)/arcCount + this.stepAngle*this.counter

      this.ctx.fillStyle = colorList[i % colorList.length]
      this.ctx.strokeStyle = colorList[i % colorList.length]
      this.ctx.beginPath()
      this.ctx.moveTo(x, y)
      this.ctx.arc(x, y, radius, startAngle, endAngle)
      this.ctx.lineTo(x, y)
      this.ctx.fill()
      this.ctx.stroke()
    }

  }

  render () {
    let overlay = null
    let mask = null
    if (this.props.onClick) {
      overlay = React.DOM.div({
        style: {
          position: 'absolute',
          height: '100%',
          width: '100%',
          backgroundColor: 'transparent'
        },
        onClick: this.click
      })
    }
    if (this.props.mask) {
      mask = React.DOM.img({
        src: 'img/mask.svg',
        style: {
          position: 'absolute',
          left: '50%',
          top: '50%',
          marginLeft: -330/2 + 'px',
          marginTop: -174/2 + 'px',
        }
      })
    }
    return React.DOM.div(
      {style: {overflow: 'hidden'}},
      React.DOM.canvas({
        ref: 'canvas',
        style: {position: 'absolute'},
        width: window.innerWidth,
        height: window.innerHeight,
      }),
      mask,
      overlay
    )
  }

}

