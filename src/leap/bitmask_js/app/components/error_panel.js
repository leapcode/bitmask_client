import React from 'react'
import Center from './center'
import Area from './area'

export default class ErrorPanel extends React.Component {

  constructor(props) {
    super(props)
  }

  render () {
    return (
      <Center width="400">
        <Area>
          <h1>Error</h1>
          {this.props.error}
        </Area>
      </Center>
    )
  }
}
