"""1: Forward-only outer tests with three earlier inner validation years."""
from common import *


def run():
    begin_step(1)
    folds = [dict(test_year=year, train_start=2010, train_end=year - 1,
                  inner_validation_years=list(range(year - 3, year)))
             for year in range(2017, 2026)]
    assert all(f['train_end'] < f['test_year'] for f in folds)
    save_json('splits.json', folds)
    finish_step(1)
    print('Step 1: 9 outer test years, 45 test province-years; no random shuffle.')
    return folds


if __name__ == '__main__':
    run()
