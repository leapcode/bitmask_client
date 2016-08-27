import React from 'react'
import {Button, ButtonGroup, ButtonToolbar, Glyphicon} from 'react-bootstrap'

import App from 'app'
import ListEdit from 'components/list_edit'
import StageLayout from './stage_layout'
import AddProviderModal from './add_provider_modal'

export default class ProviderSelectStage extends React.Component {

  static get defaultProps() {return{
    title: "Choose a provider",
    subtitle: "This doesn't work yet"
  }}

  constructor(props) {
    super(props)
    let domains = this.currentDomains()
    this.state = {
      domains: domains,
      showModal: false
    }
    this.add = this.add.bind(this)
    this.remove = this.remove.bind(this)
    this.close = this.close.bind(this)
    this.previous = this.previous.bind(this)
  }

  currentDomains() {
    // return(App.providers.domains().slice() || [])
    return ['domain1', 'domain2', 'domain3']
  }

  add() {
    this.setState({showModal: true})
  }

  remove(provider) {
    // App.providers.remove(provider)
    this.setState({domains: this.currentDomains()})
  }

  close() {
    let domains = this.currentDomains()
    if (domains.length != this.state.domains.length) {
      // this is ugly, but i could not get selection working
      // by passing it as a property
      this.refs.list.setSelected(0)
    }
    this.setState({
      domains: domains,
      showModal: false
    })
  }

  previous() {
    App.start()
  }

  render() {
    let modal = null
    if (this.state.showModal) {
      modal = <AddProviderModal onClose={this.close} />
    }
    let buttons = (
      <ButtonToolbar className="pull-right">
        <Button onClick={this.previous}>
          <Glyphicon glyph="chevron-left" />
          Previous
        </Button>
        <Button>
          Next
          <Glyphicon glyph="chevron-right" />
        </Button>
      </ButtonToolbar>
    )
    let select = <ListEdit ref="list" items={this.state.domains}
      onRemove={this.remove} onAdd={this.add} />
    return(
      <StageLayout title={this.props.title} subtitle={this.props.subtitle} buttons={buttons}>
        {select}
        {modal}
      </StageLayout>
    )
  }
}
