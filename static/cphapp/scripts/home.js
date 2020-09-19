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
      dateEnd.setDate(dateEnd.getDate() + 1);
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
      dateEnd.setDate(dateEnd.getDate() + 1);
      const args = `transaction_date__gte=${dateStart}&transaction_date__lt=${dateEnd.toLocaleDateString()}`;
      Home.fetchTransactions(args);
    };

    this.salesSummaryComponent = new SalesSummaryComponent();
    this.salesSummaryComponent.addSummary('WALLET', 0);
    this.salesSummaryComponent.addSummary('SALES', 0);
    this.salesSummaryComponent.addSummary('REBATES', 0);
    this.salesSummaryComponent.addSummary('TOP UPS', 0);
  }

  static fetchTransactions = async function (args) {
    const endpoint = '/cphapp/api/transactions/' + '?' + args;
    console.log(endpoint);
    let data = await apiService(endpoint + '&update=true');
    this.transactions.push(...data.results);
    if (data.next) {
      this.fetchTransactions(data.next);
    } else {
      console.log(this.transactions);
      Home.updateUI();
    }
  };

  static calculateSummary() {
    const firstEl = this.transactions[0];
    if (!firstEl) {
      throw Error('There are no transactions on selected range.');
    }

    const successful_sales = this.transactions.filter(
      (el) => el.transaction_type === 'sell_order' && el.status === 'success'
    );
    const wallet = firstEl.running_balance;
    const sales = successful_sales.reduce((acc, prev) => {
      return acc + prev.amount;
    }, 0);
    const rebates = successful_sales.reduce((acc, prev) => {
      return acc + prev.reward_amount;
    }, 0);
    const topUps =
      successful_sales.filter(
        (el) => el.amount < 100 && el.transaction_type === 'sell_order'
      ).length * 2;

    return {
      wallet: wallet,
      sales: sales,
      rebates: rebates,
      topUps: topUps,
    };
  }

  static updateUI() {
    const wallet = this.salesSummaryComponent.getSummary('WALLET');
    const sales = this.salesSummaryComponent.getSummary('SALES');
    const rebates = this.salesSummaryComponent.getSummary('REBATES');
    const topUps = this.salesSummaryComponent.getSummary('TOP UPS');

    let summary = null;
    try {
      summary = this.calculateSummary();
    } catch (error) {
      summary = { wallet: 0, sales: 0, rebates: 0, topUps: 0 };
    }
    wallet.updateContent(summary.wallet);
    sales.updateContent(summary.sales);
    rebates.updateContent(summary.rebates);
    topUps.updateContent(summary.topUps);
  }
}

Home.init();
