class SelectOption {
  static preselect = null;
  onselect = null;
  constructor(id, name) {
    this.id = id;
    this.name = name;
  }
}

class SelectComponent {
  #options;

  constructor(selectOptions) {
    this.#options = [];

    this.htmlElement = document.getElementById('select-component');
    this.selectHeadEl = this.htmlElement.querySelector('.select-head');
    this.selectedOptionEl = this.htmlElement.querySelector('#selected');
    this.optionsListEl = this.htmlElement.querySelector('.select-options'); // ul element
    selectOptions.forEach((option) => this.addOption(option));
    // Attach event handler selectHeadEl
    this.selectHeadEl.onclick = this.selectHeadClickHandler.bind(this);
    this.optionSelectedHandler(this.options[0]);
  }

  get selected() {
    return this._selected;
  }

  set selected(selectedOption) {
    selectedOption
      ? (this.selectedOptionEl.textContent = selectedOption.name)
      : (this.selectedOptionEl.textContent = '');
    this._selected = selectedOption;
  }

  get options() {
    return this.#options;
  }

  // Event handlers
  selectHeadClickHandler() {
    this.selectHeadEl.classList.toggle('select-expand');
    this.optionsListEl.classList.toggle('invisible');
  }

  optionSelectedHandler(selectedOption) {
    this.selected = selectedOption;
    this.optionsListEl.classList.add('invisible');
    this.selectHeadEl.classList.remove('select-expand');
    selectedOption.onselect ? selectedOption.onselect() : null;
  }

  // Methods
  addOption(option) {
    // Create new list item
    const li = document.createElement('li');
    li.textContent = option.name;
    li.id = option.id;
    // Attach event handler
    li.onclick = this.optionSelectedHandler.bind(this, option);
    this.optionsListEl.append(li);
    this.#options.push(option);
  }

  deleteOption(optionId) {
    const option = this.options.find((option) => option.id == optionId);
    const optionIndex = this.options.indexOf(option);
    this.#options.splice(optionIndex, 1);

    const optionLi = this.optionsListEl.querySelector(`#${optionId}`);
    optionLi.remove();

    if (optionLi.id === this.selected.id) {
      this.selected = null;
    }
  }
}

class DateRangePickerComponent {
  onapply = null;

  constructor() {
    this.htmlElement = document.getElementById('custom-range-picker');
    this.errorList = this.htmlElement.querySelector('#custom-range-error');
    this.dateStartWidget = this.htmlElement.querySelector('#custom-date-start');
    this.dateEndWidget = this.htmlElement.querySelector('#custom-date-end');
    this.confirmBtn = this.htmlElement.querySelector('#custom-range__apply');
    this.cancelBtn = this.htmlElement.querySelector('#custom-range__clear');

    // Attach event listeners
    this.dateStartWidget.onchange = this.clearStartDateWidgetError.bind(this);
    this.dateEndWidget.onchange = this.clearEndDateWidgetError.bind(this);
    this.confirmBtn.onclick = this.confirmBtnClickHandler.bind(this);
    this.cancelBtn.onclick = this.cancelBtnClickHandler.bind(this);
  }

  get startDate() {
    return this.dateStartWidget.valueAsDate;
  }

  get endDate() {
    return this.dateEndWidget.valueAsDate;
  }

  // Methods
  render() {
    return this.htmlElement;
  }
  clearStartDateWidgetError() {
    this.dateStartWidget.classList.remove('error');
  }
  clearEndDateWidgetError() {
    this.dateEndWidget.classList.remove('error');
  }
  clearErrors() {
    this.clearStartDateWidgetError();
    this.clearEndDateWidgetError();
    this.errorList.classList.add('invisible');
    this.errorList.innerHTML = '';
  }
  clearWidgets() {
    this.clearErrors();
    this.dateEndWidget.value = '';
    this.dateStartWidget.value = '';
  }
  show() {
    this.clearWidgets();
    this.htmlElement.classList.remove('invisible');
  }
  hide() {
    this.htmlElement.classList.add('invisible');
  }

  // Event handlers
  cancelBtnClickHandler() {
    this.clearWidgets();
  }
  confirmBtnClickHandler() {
    this.clearErrors();
    const errorList = [];
    const startDate = this.startDate;
    const endDate = this.endDate;

    if (!startDate || !endDate) {
      if (!startDate) {
        this.dateStartWidget.focus();
        this.dateStartWidget.classList.add('error');
        errorList.push('Please enter start date.');
      }
      if (!endDate) {
        this.dateEndWidget.focus();
        this.dateEndWidget.classList.add('error');
        errorList.push('Please enter end date.');
      }
    } else if (endDate - startDate < 0) {
      this.dateStartWidget.classList.add('error');
      this.dateEndWidget.classList.add('error');
      errorList.push('Invalid date range!');
    }

    if (errorList.length) {
      errorList.forEach((error) => {
        const li = document.createElement('li');
        li.textContent = error;
        this.errorList.append(li);
      });
      this.errorList.classList.remove('invisible');
    } else {
      const dateRange = {
        start: startDate,
        end: endDate,
      };
      this.onapply(dateRange);
    }
  }
}

class Summary {
  #name;
  #content;
  #card;
  constructor(name, content) {
    this.#name = name;
    this.#content = content;
    this.#card = new SalesCardComponent(this.#name, this.#content);
  }

  get name() {
    return this.#name;
  }

  get card() {
    return this.#card;
  }

  deleteCard() {
    this.#card.htmlElement.remove();
  }

  updateName(value) {
    this.#name = value;
    this.#card.title = value;
  }

  updateContent(value) {
    this.#content = value;
    this.#card.content = value;
  }
}

class SalesSummaryComponent {
  #summaryList;
  #hookElement;
  constructor() {
    this.#summaryList = [];
    this.#hookElement = document.querySelector('#sales-summary');
  }

  getSummary(title) {
    return this.#summaryList.find((el) => el.name === title);
  }

  addSummary(title, content) {
    const summary = new Summary(title, content);
    this.#summaryList.push(summary);
    this.#hookElement.append(summary.card.htmlElement);
  }

  removeSummary(title) {
    const summary = this.#summaryList.find((el) => el.title === title);
    this.#summaryList.splice(this.#summaryList.indexOf(summary), 1);
    summary.deleteCard();
  }
}

class SalesCardComponent {
  #htmlElement;
  #cardTitle;
  #cardBody;
  constructor(title, content) {
    this.#htmlElement = document.createElement('div');
    this.#htmlElement.className = 'card';
    this.#cardTitle = document.createElement('div');
    this.#cardTitle.className = 'card-title card-component';
    this.#cardBody = document.createElement('div');
    this.#cardBody.className = 'card-body card-component';
    this.#htmlElement.append(this.#cardTitle, this.#cardBody);
    this.title = title;
    this.content = content;
  }

  get title() {
    return this.#cardTitle.textContent;
  }
  set title(value) {
    this.#cardTitle.textContent = value;
  }
  get content() {
    return this.#cardBody.textContent;
  }
  set content(value) {
    this.#cardBody.textContent = value;
  }
  get htmlElement() {
    return this.#htmlElement;
  }
}

export {
  SelectOption,
  SelectComponent,
  DateRangePickerComponent,
  SalesSummaryComponent,
};
