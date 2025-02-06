export function setMidnight(date) {
    const d = new Date(date);
    d.setHours(0, 0, 0, 0);
    return d;
}

export function setEndOfDay(date) {
    const d = new Date(date);
    d.setHours(23, 59, 59, 999);
    return d;
}

export function getStartOfWeek(date) {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust for Sunday
    d.setDate(diff);
    return setMidnight(d);
}

export function getEndOfWeek(date) {
    const d = getStartOfWeek(date);
    d.setDate(d.getDate() + 6);
    return setEndOfDay(d);
}

export function getStartOfMonth(date) {
    const d = new Date(date);
    d.setDate(1);
    return setMidnight(d);
}

export function getEndOfMonth(date) {
    const d = new Date(date);
    d.setMonth(d.getMonth() + 1);
    d.setDate(0);
    return setEndOfDay(d);
}

export function getStartOfQuarter(date) {
    const d = new Date(date);
    const month = d.getMonth();
    d.setMonth(Math.floor(month / 3) * 3);
    d.setDate(1);
    return setMidnight(d);
}

export function getEndOfQuarter(date) {
    const d = getStartOfQuarter(date);
    d.setMonth(d.getMonth() + 3);
    d.setDate(0);
    return setEndOfDay(d);
}

export function getQuarterName(date) {
    const month = date.getMonth();
    const quarter = Math.floor(month / 3) + 1;
    return `Q${quarter}`;
}

export function getStartOfYear(date) {
    const d = new Date(date);
    d.setMonth(0);
    d.setDate(1);
    return setMidnight(d);
}

export function getEndOfYear(date) {
    const d = new Date(date);
    d.setMonth(11);
    d.setDate(31);
    return setEndOfDay(d);
}

// Constants
export const EARLIEST_DATE = setMidnight(new Date('2022-03-23T00:00:00'));
export const TODAY = setMidnight(new Date());
export const TOTAL_DAYS = Math.floor((TODAY - EARLIEST_DATE) / (1000 * 60 * 60 * 24));
export const TOTAL_WEEKS = Math.floor(TOTAL_DAYS / 7);
export const TOTAL_MONTHS = (TODAY.getFullYear() - EARLIEST_DATE.getFullYear()) * 12 + 
                          (TODAY.getMonth() - EARLIEST_DATE.getMonth());
export const TOTAL_QUARTERS = Math.floor((TODAY.getFullYear() - EARLIEST_DATE.getFullYear()) * 4 + 
                            Math.floor(TODAY.getMonth() / 3) - Math.floor(EARLIEST_DATE.getMonth() / 3));
export const TOTAL_YEARS = TODAY.getFullYear() - EARLIEST_DATE.getFullYear();

export function getUnitMax(unit) {
    switch(unit) {
        case 'day': return TOTAL_DAYS;
        case 'week': return TOTAL_WEEKS;
        case 'month': return TOTAL_MONTHS;
        case 'quarter': return TOTAL_QUARTERS;
        case 'year': return TOTAL_YEARS;
        default: return TOTAL_DAYS;
    }
}

export function unitsToDate(units, unit, max, isEnd = false) {
    // Return null for end date at max value to indicate "now"
    if (units === max && isEnd) {
        return null;
    }

    let date = new Date(EARLIEST_DATE);
    switch(unit) {
        case 'day':
            date.setDate(date.getDate() + units);
            return isEnd ? setEndOfDay(date) : setMidnight(date);
        case 'week':
            date.setDate(date.getDate() + (units * 7));
            if (isEnd && units === max) {
                return null;
            }
            return isEnd ? getEndOfWeek(date) : getStartOfWeek(date);
        case 'month':
            date.setMonth(date.getMonth() + units);
            return isEnd ? getEndOfMonth(date) : getStartOfMonth(date);
        case 'quarter':
            const startYear = EARLIEST_DATE.getFullYear();
            const startQuarter = Math.floor(EARLIEST_DATE.getMonth() / 3);
            const totalQuarters = units;
            const targetYear = startYear + Math.floor((startQuarter + totalQuarters) / 4);
            const targetQuarter = (startQuarter + totalQuarters) % 4;
            
            date = new Date(targetYear, targetQuarter * 3, 1);
            if (isEnd && units === max) {
                return null;
            }
            return isEnd ? getEndOfQuarter(date) : setMidnight(date);
        case 'year':
            date.setFullYear(date.getFullYear() + units);
            return isEnd ? getEndOfYear(date) : getStartOfYear(date);
    }
    return date;
}
