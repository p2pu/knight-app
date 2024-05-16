import React from 'react'
import ReactDOM from 'react-dom'
import MobileInput from './components/mobile-input'

const element = document.getElementById('div_id_mobile');

if (element) {
  let label = element.querySelector('label');
  let hint = element.querySelector('#div_id_mobile .form-text');
  let error = element.querySelector('#error_1_id_mobile');
  let input = element.querySelector('#id_mobile');

  ReactDOM.render(
    <MobileInput
      label={label.textContent}
      hint={hint.textContent}
      error={error?error.textContent:null}
      value={input.value}
    />,
    document.getElementById('div_id_mobile')
  );
}
