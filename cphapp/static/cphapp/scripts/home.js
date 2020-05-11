import {
  SelectOption,
  SelectComponent,
  DateRangePickerComponent,
  SalesSummaryComponent,
} from './modules/components.js';

import {
  dateRangeToday,
  dateRangeYesterday,
  dateRangeThisWeek,
  dateRangeThisMonth,
} from './utils/utils.js';

import { apiService } from '/static/assets/scripts/api.service.js';

class Home {
  static transactions = [];

  static init() {
    this.customDateRangePickerComponent = new DateRangePickerComponent();
    const today = new SelectOption('option0', 'Today');
    const yesterday = new SelectOption('option1', 'Yesterday');
    const thisWeek = new SelectOption('option2', 'This Week');
    const lastWeek = new SelectOption('option3', 'Last Week');
    const thisMonth = new SelectOption('option4', 'This Month');
    const customRange = new SelectOption('option5', 'Custom Range');

    // Attach event listeners
    today.onselect = () => {
      Home.customDateRangePickerComponent.hide();
      Home.transactions = [];
      const dateRange = dateRangeToday();
      const year = dateRange.start.getFullYear();
      const month = dateRange.start.getMonth();
      const day = dateRange.start.getDate();
      const args = `transaction_date__year=${year}&transaction_date__month=${
        month + 1
      }&transaction_date__day=${day}`;
      Home.fetchTransactions(args);
    };
    yesterday.onselect = () => {
      Home.customDateRangePickerComponent.hide();
      Home.transactions = [];
      const dateRange = dateRangeYesterday();
      const year = dateRange.start.getFullYear();
      const month = dateRange.start.getMonth();
      const day = dateRange.start.getDate();
      const args = `transaction_date__year=${year}&transaction_date__month=${
        month + 1
      }&transaction_date__day=${day}`;
      Home.fetchTransactions(args);
    };
    thisWeek.onselect = () => {
      Home.customDateRangePickerComponent.hide();
      Home.transactions = [];
      const dateRange = dateRangeThisWeek();
      const dateStart = dateRange.start.toLocaleDateString();
      const dateEnd = dateRange.end;
      dateEnd.setDate(dateEnd.getDate() + 1)
      const args = `transaction_date__gte=${dateStart}&transaction_date__lt=${dateEnd.toLocaleDateString()}`;
      Home.fetchTransactions(args);
    };
    thisMonth.onselect = () => {
      Home.customDateRangePickerComponent.hide();
      Home.transactions = [];
      const dateRange = dateRangeThisMonth();
      const dateStart = dateRange.start;
      const dateEnd = dateRange.end.toLocaleDateString();
      const args = `transaction_date__year=${dateStart.getFullYear()}&transaction_date__month=${
        dateStart.getMonth() + 1
      }`;
      Home.fetchTransactions(args);
    };
    customRange.onselect = () => {
      Home.customDateRangePickerComponent.show();
      Home.transactions = [];
    };

    this.dateRangeSelectComponent = new SelectComponent([
      today,
      yesterday,
      thisWeek,
      thisMonth,
      customRange,
    ]);

    this.customDateRangePickerComponent.onapply = (dateRange) => {
      Home.transactions = [];
      const dateStart = dateRange.start.toLocaleDateString();
      const dateEnd = dateRange.end;
      dateEnd.setDate(dateEnd.getDate() + 1)
      const args = `transaction_date__gte=${dateStart}&transaction_date__lt=${dateEnd.toLocaleDateString()}`;
      Home.fetchTransactions(args);
    };

    this.salesSummaryComponent = new SalesSummaryComponent();
    this.salesSummaryComponent.addSummary('WALLET', 0);
    this.salesSummaryComponent.addSummary('SALES', 0);
    this.salesSummaryComponent.addSummary('REBATES', 0);
    this.salesSummaryComponent.addSummary('TOP UPS', 0);
  }

  static fetchTransactions(args) {
    const endpoint = '/cphapp/api/transactions/' + '?' + args;
    console.log(endpoint);
    apiService(endpoint).then((data) => {
      console.log(data);
      this.transactions.push(...data.results);
      if (data.next) {
        this.fetchTransactions(data.next);
      } else {
        console.log(this.transactions);
        Home.updateUI();
      }
    });
  }

  static calculateSummary() {
    const firstEl = this.transactions[0];
    if (!firstEl) {
      return;
    }
    const wallet = firstEl.running_balance;
    const sales = this.transactions.reduce((acc, prev) => {
      return acc + prev.sell_amount;
    }, 0);
    const rebates = this.transactions.reduce((acc, prev) => {
      return acc + prev.reward_amount;
    }, 0);
    const topUps =
      this.transactions.filter(
        (el) => el.sell_amount < 100 && el.transaction_type === 'sell'
      ).length * 2;

    return {
      wallet: wallet,
      sales: sales,
      rebates: rebates,
      topUps: topUps,
    };
  }

  static updateUI() {
    const summary = this.calculateSummary();
    const wallet = this.salesSummaryComponent.getSummary('WALLET');
    const sales = this.salesSummaryComponent.getSummary('SALES');
    const rebates = this.salesSummaryComponent.getSummary('REBATES');
    const topUps = this.salesSummaryComponent.getSummary('TOP UPS');
    console.log(wallet);
    wallet.updateContent(summary.wallet);
    sales.updateContent(summary.sales);
    rebates.updateContent(summary.rebates);
    topUps.updateContent(summary.topUps);
  }
}

Home.init();
