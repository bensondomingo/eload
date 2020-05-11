const dateRangeToday = function () {
  const today = new Date();
  return {
    start: today,
    end: today,
  };
};

const dateRangeYesterday = function () {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  return {
    start: yesterday,
    end: yesterday,
  };
};

const dateRangeThisWeek = function () {
  const today = new Date();
  const weekStartDate = new Date();
  const weekEndDate = new Date();
  weekStartDate.setDate(today.getDate() - today.getDay());
  weekEndDate.setDate(today.getDate() + (6 - today.getDay()));
  return {
    start: weekStartDate,
    end: weekEndDate,
  };
};

const dateRangeThisMonth = function () {
  const today = new Date();
  const monthStartDate = new Date(today.getFullYear(), today.getMonth());
  const monthEndDAte = new Date(today.getFullYear(), today.getMonth() + 1, 0);
  return {
    start: monthStartDate,
    end: monthEndDAte,
  };
};

export {
  dateRangeToday,
  dateRangeYesterday,
  dateRangeThisWeek,
  dateRangeThisMonth,
};
