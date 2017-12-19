from hypothesis import given, assume
from hypothesis.strategies import (data, dictionaries, just,
                                   integers, tuples, lists, sets)
from pytest import raises

from segpy.catalog import CatalogBuilder, RowMajorCatalog2D, DictionaryCatalog, DictionaryCatalog2D, \
    RegularConstantCatalog, ConstantCatalog, RegularCatalog
from segpy.sorted_set import SortedFrozenSet
from segpy.util import is_totally_sorted
from test.predicates import check_balanced
from test.strategies import ranges, items2d


class TestCatalogBuilder:

    def test_unspecified_mapping_returns_empty_catalog(self):
        builder = CatalogBuilder()
        catalog = builder.create()
        assert len(catalog) == 0

    def test_empty_mapping_returns_empty_catalog(self):
        builder = CatalogBuilder([])
        catalog = builder.create()
        assert len(catalog) == 0

    def test_mapping_is_neither_dictionary_nor_iterable_raises_type_error(self):
        with raises(TypeError):
            CatalogBuilder(42)

    def test_mapping_iterable_does_not_contain_pairs_raises_value_error(self):
        with raises(ValueError):
            CatalogBuilder([(1, 2, 3)])

    @given(lists(min_size=1, elements=tuples(integers(), integers())))
    def test_duplicate_items_returns_none(self, mapping):
        builder = CatalogBuilder(mapping + mapping)
        catalog = builder.create()
        assert catalog is None

    @given(dictionaries(integers(), integers()))
    def test_arbitrary_mapping(self, mapping):
        builder = CatalogBuilder(mapping)
        catalog = builder.create()
        shared_items = set(mapping.items()) & set(catalog.items())
        assert len(shared_items) == len(mapping)

    @given(dictionaries(integers(), just(42)))
    def test_constant_mapping(self, mapping):
        builder = CatalogBuilder(mapping)
        catalog = builder.create()
        shared_items = set(mapping.items()) & set(catalog.items())
        assert len(shared_items) == len(mapping)

    @given(start=integers(),
           num=integers(0, 1000),
           step=integers(-1000, 1000),
           value=integers())
    def test_regular_constant_mapping(self, start, num, step, value):
        assume(step != 0)
        mapping = {key: value for key in range(
            start, start + num * step, step)}
        builder = CatalogBuilder(mapping)
        catalog = builder.create()
        shared_items = set(mapping.items()) & set(catalog.items())
        assert len(shared_items) == len(mapping)

    @given(start=integers(),
           num=integers(0, 1000),
           step=integers(-1000, 1000),
           values=data())
    def test_regular_mapping(self, start, num, step, values):
        assume(step != 0)
        mapping = {key: values.draw(integers())
                   for key
                   in range(start, start + num * step, step)}
        builder = CatalogBuilder(mapping)
        catalog = builder.create()
        shared_items = set(mapping.items()) & set(catalog.items())
        assert len(shared_items) == len(mapping)

    @given(num=integers(0, 1000),
           key_start=integers(),
           key_step=integers(-1000, 1000),
           value_start=integers(),
           value_step=integers(-1000, 1000))
    def test_linear_regular_mapping(self, num, key_start, key_step, value_start, value_step):
        assume(key_step != 0)
        assume(value_step != 0)
        mapping = {key: value for key, value in zip(range(key_start, key_start + num * key_step, key_step),
                                                    range(value_start, value_start + num * value_step, value_step))}
        builder = CatalogBuilder(mapping)
        catalog = builder.create()
        shared_items = set(mapping.items()) & set(catalog.items())
        assert len(shared_items) == len(mapping)

    @given(dictionaries(tuples(integers(), integers()), integers()))
    def test_arbitrary_mapping_2d(self, mapping):
        builder = CatalogBuilder(mapping)
        catalog = builder.create()
        shared_items = set(mapping.items()) & set(catalog.items())
        assert len(shared_items) == len(mapping)

    @given(i_start=integers(0, 10),
           i_num=integers(1, 10),
           i_step=just(1),
           j_start=integers(0, 10),
           j_num=integers(1, 10),
           j_step=just(1),
           c=integers(1, 10))
    def test_linear_regular_mapping_2d(self, i_start, i_num, i_step, j_start, j_num, j_step, c):
        assume(i_step != 0)
        assume(j_step != 0)

        def v(i, j):
            return (i - i_start) * ((j_start + j_num * j_step) - j_start) + (j - j_start) + c

        mapping = {(i, j): v(i, j)
                   for i in range(i_start, i_start + i_num * i_step, i_step)
                   for j in range(j_start, j_start + j_num * j_step, j_step)}

        builder = CatalogBuilder(mapping)
        catalog = builder.create()
        shared_items = set(mapping.items()) & set(catalog.items())
        assert len(shared_items) == len(mapping)

    @given(mapping=dictionaries(keys=integers(), values=integers()))
    def test_adding_items_puts_them_in_the_catalog(self, mapping):
        builder = CatalogBuilder()
        for key, value in mapping.items():
            builder.add(key, value)
        catalog = builder.create()
        assert all(catalog[key] == value for key, value in mapping.items())

    def test_irregular_mapping_gives_dictionary_catalog(self):
        mapping = {
            1: 2,
            2: 3,
            3: 5,
            5: 7,
            8: 11,
            13: 13,
            21: 17,
            34: 19,
            55: 23,
            89: 29,
            144: 31,
        }
        builder = CatalogBuilder(mapping)
        catalog = builder.create()
        assert all(catalog[key] == value for key, value in mapping.items())


class TestRowMajorCatalog2D:

    @given(i_range=ranges(min_size=1, min_step_value=1),
           j_range=ranges(min_size=1, min_step_value=1),
           constant=integers())
    def test_irange_preserved(self, i_range, j_range, constant):
        catalog = RowMajorCatalog2D(i_range, j_range, constant)
        assert catalog.i_range == i_range

    @given(i_range=ranges(min_size=1, min_step_value=1),
           j_range=ranges(min_size=1, min_step_value=1),
           constant=integers())
    def test_jrange_preserved(self, i_range, j_range, constant):
        catalog = RowMajorCatalog2D(i_range, j_range, constant)
        assert catalog.j_range == j_range

    @given(i_range=ranges(min_size=1, min_step_value=1),
           j_range=ranges(min_size=1, min_step_value=1),
           constant=integers())
    def test_constant_preserved(self, i_range, j_range, constant):
        catalog = RowMajorCatalog2D(i_range, j_range, constant)
        assert catalog.constant == constant

    @given(i_range=ranges(min_size=1, min_step_value=1),
           j_range=ranges(min_size=1, min_step_value=1),
           constant=integers())
    def test_i_min(self, i_range, j_range, constant):
        catalog = RowMajorCatalog2D(i_range, j_range, constant)
        assert catalog.i_min == i_range.start

    @given(i_range=ranges(min_size=1, min_step_value=1),
           j_range=ranges(min_size=1, min_step_value=1),
           constant=integers())
    def test_i_max(self, i_range, j_range, constant):
        catalog = RowMajorCatalog2D(i_range, j_range, constant)
        assert catalog.i_max == i_range.stop - i_range.step

    @given(i_range=ranges(min_size=1, min_step_value=1),
           j_range=ranges(min_size=1, min_step_value=1),
           constant=integers())
    def test_j_min(self, i_range, j_range, constant):
        catalog = RowMajorCatalog2D(i_range, j_range, constant)
        assert catalog.j_min == j_range.start

    @given(i_range=ranges(min_size=1, min_step_value=1),
           j_range=ranges(min_size=1, min_step_value=1),
           constant=integers())
    def test_j_max(self, i_range, j_range, constant):
        catalog = RowMajorCatalog2D(i_range, j_range, constant)
        assert catalog.j_max == j_range.stop - j_range.step

    @given(i_range=ranges(min_size=1, min_step_value=1),
           j_range=ranges(min_size=1, min_step_value=1),
           constant=integers())
    def test_key_min(self, i_range, j_range, constant):
        catalog = RowMajorCatalog2D(i_range, j_range, constant)
        assert catalog.key_min() == (i_range.start, j_range.start)

    @given(i_range=ranges(min_size=1, min_step_value=1),
           j_range=ranges(min_size=1, min_step_value=1),
           constant=integers())
    def test_key_max(self, i_range, j_range, constant):
        catalog = RowMajorCatalog2D(i_range, j_range, constant)
        assert catalog.key_max() == (i_range.stop - i_range.step,
                                     j_range.stop - j_range.step)

    @given(i_range=ranges(min_size=1, min_step_value=1),
           j_range=ranges(min_size=1, min_step_value=1),
           constant=integers())
    def test_value_start(self, i_range, j_range, constant):
        catalog = RowMajorCatalog2D(i_range, j_range, constant)
        assert catalog.value_start() == constant

    @given(i_range=ranges(min_size=1, min_step_value=1),
           j_range=ranges(min_size=1, min_step_value=1),
           constant=integers())
    def test_value_stop(self, i_range, j_range, constant):
        catalog = RowMajorCatalog2D(i_range, j_range, constant)
        # for key, value in catalog.items():
        #     print(key, value)
        # print()
        i_min = i_range.start
        i_max = i_range.stop - i_range.step
        j_min = j_range.start
        j_max = j_range.stop - j_range.step
        assert catalog.value_stop() == (i_max - i_min) * (j_max + 1 - j_min) + (j_max - j_min) + constant

    @given(i_range=ranges(min_size=1, min_step_value=1),
           j_range=ranges(min_size=1, min_step_value=1),
           constant=integers())
    def test_repr(self, i_range, j_range, constant):
        catalog = RowMajorCatalog2D(i_range, j_range, constant)
        r = repr(catalog)
        assert r.startswith('RowMajorCatalog2D')
        assert 'i_range={!r}'.format(i_range) in r
        assert 'j_range={!r}'.format(j_range) in r
        assert 'constant={!r}'.format(constant) in r
        assert check_balanced(r)

    def test_row_major_example(self):
        mapping = {
            (0, 4): 8,
            (0, 5): 9,
            (0, 6): 10,
            (1, 4): 11,
            (1, 5): 12,
            (1, 6): 13,
            (2, 4): 14,
            (2, 5): 15,
            (2, 6): 16
        }
        catalog_builder = CatalogBuilder(mapping)
        catalog = catalog_builder.create()
        assert isinstance(catalog, RowMajorCatalog2D)
        assert catalog.key_min() == (0, 4)
        assert catalog.key_max() == (2, 6)
        assert catalog.value_start() == 8
        assert catalog.value_stop() == 16
        assert catalog.constant == 8
        assert catalog.i_min == 0
        assert catalog.i_max == 2
        assert catalog.j_min == 4
        assert catalog.j_max == 6
        assert len(catalog) == 9

        with raises(KeyError):
            catalog[(0, 0)]


class TestDictionaryCatalog:

    @given(dictionaries(integers(), integers()))
    def test_items_keys_are_present(self, items):
        catalog = DictionaryCatalog(items)
        assert all(key in catalog for key in items.keys())

    @given(dictionaries(integers(), integers()))
    def test_items_keys_are_preserved(self, items):
        catalog = DictionaryCatalog(items)
        assert all(catalog[key] == value for key, value in items.items())

    @given(dictionaries(integers(), integers()))
    def test_length(self, items):
        catalog = DictionaryCatalog(items)
        assert len(catalog) == len(items)

    @given(dictionaries(integers(min_value=0, max_value=1000), integers(min_value=0, max_value=1000)))
    def test_repr(self, items):
        catalog = DictionaryCatalog(items)
        r = repr(catalog)
        assert r.startswith('DictionaryCatalog')
        assert check_balanced(r)


class TestDictionaryCatalog2D:

    @given(items2d(10, 10))
    def test_irange_preserved(self, items):
        catalog = DictionaryCatalog2D(items.i_range, items.j_range, items.items)
        assert catalog.i_range == items.i_range

    @given(items2d(10, 10))
    def test_jrange_preserved(self, items):
        catalog = DictionaryCatalog2D(items.i_range, items.j_range, items.items)
        assert catalog.j_range == items.j_range

    @given(i_range=lists(integers(), min_size=2),
           j_range=ranges(min_size=1, max_size=100, min_step_value=1),
           items=dictionaries(integers(min_value=0, max_value=1000), integers(min_value=0, max_value=1000)))
    def test_unsorted_irange_raises_value_error(self, i_range, j_range, items):
        assume(not is_totally_sorted(i_range))
        with raises(ValueError):
            DictionaryCatalog2D(i_range, j_range, items)

    @given(i_range=ranges(min_size=1, max_size=100, min_step_value=1),
           j_range=lists(integers(), min_size=2),
           items=dictionaries(integers(min_value=0, max_value=1000), integers(min_value=0, max_value=1000)))
    def test_unsorted_jrange_raises_value_error(self, i_range, j_range, items):
        assume(not is_totally_sorted(j_range))
        with raises(ValueError):
            DictionaryCatalog2D(i_range, j_range, items)

    @given(items2d(10, 10))
    def test_length(self, items):
        catalog = DictionaryCatalog2D(items.i_range, items.j_range, items.items)
        assert len(catalog) == len(items.items)

    @given(items2d(10, 10))
    def test_repr(self, items):
        catalog = DictionaryCatalog2D(items.i_range, items.j_range, items.items)
        r = repr(catalog)
        assert r.startswith('DictionaryCatalog')
        assert 'i_range={!r}'.format(items.i_range) in r
        assert 'j_range={!r}'.format(items.j_range) in r
        assert check_balanced(r)


class TestRegularConstantCatalog:

    def test_key_min_greater_than_key_max_raises_value_error(self):
        with raises(ValueError):
            RegularConstantCatalog(11, 10, 3, 0)

    def test_illegal_stride_raises_value_error(self):
        with raises(ValueError):
            RegularConstantCatalog(0, 10, 3, 0)

    @given(r=ranges(min_size=1, max_size=100, min_step_value=1),
           c=integers(),
           k=integers())
    def test_missing_key_raises_key_error(self, r, c, k):
        assume(k not in r)
        catalog = RegularConstantCatalog(r.start, r[-1], r.step, c)
        with raises(KeyError):
            catalog[k]

    @given(r=ranges(min_size=1, max_size=100, min_step_value=1),
           c=integers())
    def test_mapping_is_preserved(self, r, c):
        catalog = RegularConstantCatalog(r.start, r[-1], r.step, c)
        assert all(catalog[key] == c for key in r)

    @given(r=ranges(min_size=1, max_size=100, min_step_value=1),
           c=integers())
    def test_length(self, r, c):
        catalog = RegularConstantCatalog(r.start, r[-1], r.step, c)
        assert len(catalog) == len(r)

    @given(r=ranges(min_size=1, max_size=100, min_step_value=1),
           c=integers())
    def test_containment(self, r, c):
        catalog = RegularConstantCatalog(r.start, r[-1], r.step, c)
        assert all(key in catalog for key in r)

    @given(r=ranges(min_size=1, max_size=100, min_step_value=1),
           c=integers())
    def test_iteration(self, r, c):
        catalog = RegularConstantCatalog(r.start, r[-1], r.step, c)
        assert all(k == m for k, m in zip(iter(catalog), r))

    @given(r=ranges(min_size=1, max_size=100, min_step_value=1),
           c=integers())
    def test_repr(self, r, c):
        catalog = RegularConstantCatalog(r.start, r[-1], r.step, c)
        r = repr(catalog)
        assert r.startswith('RegularConstantCatalog')
        assert 'key_min={}'.format(catalog._key_min) in r
        assert 'key_max={}'.format(catalog._key_max) in r
        assert 'key_stride={}'.format(catalog._key_stride) in r
        assert check_balanced(r)


class TestConstantCatalog:

    @given(keys=lists(integers()),
           value=integers(),
           k=integers())
    def test_missing_key_raises_key_error(self, keys, value, k):
        assume(k not in keys)
        catalog = ConstantCatalog(keys, value)
        with raises(KeyError):
            catalog[k]

    @given(keys=lists(integers()),
           value=integers())
    def test_mapping_is_preserved(self, keys, value):
        catalog = ConstantCatalog(keys, value)
        assert all(catalog[key] == value for key in keys)

    @given(keys=sets(integers()),
           value=integers())
    def test_length(self, keys, value):
        catalog = ConstantCatalog(keys, value)
        assert len(catalog) == len(keys)

    @given(keys=lists(integers()),
           value=integers())
    def test_containment(self, keys, value):
        catalog = ConstantCatalog(keys, value)
        assert all(key in catalog for key in keys)

    @given(keys=lists(integers()),
           value=integers())
    def test_iteration(self, keys, value):
        s = SortedFrozenSet(keys)
        catalog = ConstantCatalog(keys, value)
        assert all(k == m for k, m in zip(iter(catalog), s))

    @given(keys=lists(integers()),
           value=integers())
    def test_repr(self, keys, value):
        catalog = ConstantCatalog(keys, value)
        r = repr(catalog)
        assert r.startswith('ConstantCatalog')
        assert 'keys=[{} items]'.format(len(catalog._keys)) in r
        assert 'value={}'.format(catalog._value) in r
        assert check_balanced(r)


class TestRegularCatalog:

    def test_key_min_greater_than_key_max_raises_value_error(self):
        with raises(ValueError):
            RegularCatalog(11, 10, 2, [0])

    def test_illegal_stride_raises_value_error(self):
        with raises(ValueError):
            RegularCatalog(0, 10, 3, [0])

    @given(r=ranges(min_size=1, max_size=100, min_step_value=1),
           d=data())
    def test_mismatched_values_length_raises_value_error(self, r, d):
        values = d.draw(lists(integers()))
        assume(len(values) != len(r))
        with raises(ValueError):
            RegularCatalog(r.start, r[-1], r.step, values)

    @given(r=ranges(min_size=1, max_size=100, min_step_value=1),
           d=data())
    def test_missing_key_raises_key_error(self, r, d):
        values = d.draw(lists(integers(), min_size=len(r), max_size=len(r)))
        k = d.draw(integers())
        assume(k not in r)
        catalog = RegularCatalog(r.start, r[-1], r.step, values)
        with raises(KeyError):
            catalog[k]

    def test_missing_key_raises_key_error_2(self):
        catalog = RegularCatalog(0, 6, 2, [0, 2, 4, 6])
        with raises(KeyError):
            catalog[1]

    @given(r=ranges(min_size=1, max_size=100, min_step_value=1),
           d=data())
    def test_mapping_is_preserved(self, r, d):
        values = d.draw(lists(integers(), min_size=len(r), max_size=len(r)))
        catalog = RegularCatalog(r.start, r[-1], r.step, values)
        assert all(catalog[k] == v for k, v in zip(r, values))

    @given(r=ranges(min_size=1, max_size=100, min_step_value=1),
           d=data())
    def test_length(self, r, d):
        values = d.draw(lists(integers(), min_size=len(r), max_size=len(r)))
        catalog = RegularCatalog(r.start, r[-1], r.step, values)
        assert len(catalog) == len(r)

    @given(r=ranges(min_size=1, max_size=100, min_step_value=1),
           d=data())
    def test_containment(self, r, d):
        values = d.draw(lists(integers(), min_size=len(r), max_size=len(r)))
        catalog = RegularCatalog(r.start, r[-1], r.step, values)
        assert all(key in catalog for key in r)

    @given(r=ranges(min_size=1, max_size=100, min_step_value=1),
           d=data())
    def test_iteration(self, r, d):
        values = d.draw(lists(integers(), min_size=len(r), max_size=len(r)))
        catalog = RegularCatalog(r.start, r[-1], r.step, values)
        assert all(k == m for k, m in zip(iter(catalog), r))

    @given(r=ranges(min_size=1, max_size=100, min_step_value=1),
           d=data())
    def test_repr(self, r, d):
        values = d.draw(lists(integers(), min_size=len(r), max_size=len(r)))
        catalog = RegularCatalog(r.start, r[-1], r.step, values)
        r = repr(catalog)
        assert r.startswith('RegularCatalog')
        assert 'key_min={}'.format(catalog._key_min) in r
        assert 'key_max={}'.format(catalog._key_max) in r
        assert 'key_stride={}'.format(catalog._key_stride) in r
        assert 'values=[{} items]'.format(len(catalog._values)) in r
        assert check_balanced(r)
