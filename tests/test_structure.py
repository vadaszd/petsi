from petsi import Net
from inspect import cleandoc
from unittest import TestCase, main
from unittest.mock import Mock


class StructureTest(TestCase):
    def test_net_building(self):
        net = Net("test net")
        self.assertEqual(net.name, "test net")

        net.add_type("my type")
        with self.assertRaisesRegex(ValueError, "Type 'my type' is already defined in net 'test net'"):
            net.add_type("my type")

        with self.assertRaisesRegex(ValueError, "Type 'wrong type' does not exist in this net "
                                                "\\(it has to be added to the net first\\)"):
            net.add_place("place 1", "wrong type", "wrong policy")

        with self.assertRaisesRegex(ValueError, "Unknown queueing policy: 'wrong policy'"):
            net.add_place("place 1", "my type", "wrong policy")

        net.add_place("place 1", "my type", "FIFO")

        with self.assertRaisesRegex(ValueError, "Place 'place 1' already exists in net 'test net'"):
            net.add_place("place 1", "my type", "wrong policy")

        net.add_place("place 2", "my type", "LIFO")

        with self.assertRaisesRegex(ValueError, "The priority of immediate transition "
                                                "'t1' must be a positive integer"):
            net.add_immediate_transition("t1", 0, 0)

        for w in (0, 0.0, 1):
            with self.assertRaisesRegex(ValueError, "The weight of immediate transition "
                                                    "'t1' must be a positive float"):
                net.add_immediate_transition("t1", 1, w)

        net.add_immediate_transition("t1", 1, 1.)

        with self.assertRaisesRegex(ValueError, "A transition with name 't1' already exists in net 'test net'."):
            net.add_timed_transition("t1", lambda: 0.1)

        net.add_timed_transition("t2", lambda: 0.1)

        net.add_constructor("arrivals", "t1", "place 1")

        with self.assertRaisesRegex(ValueError, "An Arc with name 'arrivals' already exists on Transition 't1'"):
            net.add_constructor("arrivals", "t1", "place 1")

        net.add_destructor("departures", "place 1", "t1", )

        net.add_type("your type")
        net.add_place("place 3", "your type", "LIFO")
        with self.assertRaisesRegex(ValueError, "Type mismatch on TransferArc\\('transfers'\\): "
                                                "type\\(place 1\\) is Type\\('my type'\\) whereas "
                                                "type\\(place 3\\) is Type\\('your type'\\)"):
            net.add_transfer("transfers", "place 1", "t1", "place 3")

        net.add_transfer("transfers", "place 1", "t1", "place 2")
# FIXME: a transition can have at most 1 iput arc per place
    def test_input_arc_enablement_status(self): pass

    def test_net_building_attaches_observers(self):
        net = Net("test net")
        net.add_type("my type")

        observer = Mock()
        observer.configure_mock(name='observer #1')

        net.register_observer(observer)
        with self.assertRaisesRegex(ValueError, "An observer with name 'observer #1' is already registered."):
            net.register_observer(observer)

        p1 = net.add_place("place 1", "my type", "FIFO")
        observer.observe_place.assert_called_with(p1)
        self.assertTrue(observer.observe_place.return_value in p1._place_observers)

        t1 = net.add_immediate_transition("t1", 1, 1.)
        observer.observe_transition.assert_called_with(t1)
        self.assertTrue(observer.observe_transition.return_value in t1._transition_observers)

        self.assertEqual(fff(observer.mock_calls),
                         cleandoc("""observe_place
                                     observe_transition
                                     observe_transition().got_enabled"""))

        observer2 = Mock()
        observer2.configure_mock(name='observer #2')

        net.register_observer(observer2)
        observer2.observe_place.assert_called_with(p1)
        self.assertTrue(observer2.observe_place.return_value in p1._place_observers)
        observer2.observe_transition.assert_called_with(t1)
        self.assertTrue(observer2.observe_transition.return_value in t1._transition_observers)

        self.assertEqual(fff(observer2.mock_calls),
                         cleandoc("""observe_transition
                                     observe_transition().got_enabled
                                     observe_place"""))

    def test_firing(self):

        net = Net("test net")
        net.add_type("my type")
        p1 = net.add_place("place 1", "my type", "FIFO")
        p2 = net.add_place("place 2", "my type", "FIFO")
        source = net.add_immediate_transition("source", 1, 1.)
        mover = net.add_immediate_transition("mover", 1, 1.)
        sink = net.add_immediate_transition("sink", 1, 1.)
        net.add_constructor("arrivals", "source", "place 1")
        net.add_transfer("transfers", "place 1", "mover", "place 2")
        net.add_destructor("departures", "place 2", "sink", )

        self.assertTrue(p1.is_empty)
        self.assertTrue(p2.is_empty)
        source.fire()
        self.assertFalse(p1.is_empty)
        self.assertTrue(p2.is_empty)
        mover.fire()
        self.assertTrue(p1.is_empty)
        self.assertFalse(p2.is_empty)
        sink.fire()
        self.assertTrue(p1.is_empty)
        self.assertTrue(p2.is_empty)

    def test_firing_notifies_observers(self):

        net = Net("test net")
        observer = Mock()
        net.register_observer(observer)
        net.add_type("my type")
        net.add_place("place 1", "my type", "FIFO")
        source = net.add_immediate_transition("source", 1, 1.)
        net.add_constructor("arrivals", "source", "place 1")
        test = net.add_immediate_transition("test transition", 1, 1.1)
        net.add_test("test arc", "place 1", "test transition")
        net.add_place("place 2", "my type", "FIFO")
        move = net.add_immediate_transition("move", 1, 1.)
        net.add_transfer("transfers", "place 1", "move", "place 2")
        sink = net.add_immediate_transition("sink", 1, 1.)
        net.add_destructor("departures", "place 2", "sink", )

        source.fire()
        test.fire()
        move.fire()

        with self.assertRaises(AssertionError):
            test.fire()

        sink.fire()

        self.maxDiff = None
        self.assertEqual(fff(observer.mock_calls),
                         cleandoc(""" observe_place
                                      observe_transition
                                      observe_transition().got_enabled
                                      observe_transition
                                      observe_transition().got_enabled
                                      observe_transition().got_disabled
                                      observe_place
                                      observe_transition
                                      observe_transition().got_enabled
                                      observe_transition().got_disabled
                                      observe_transition
                                      observe_transition().got_enabled
                                      observe_transition().got_disabled
                                      observe_transition().before_firing
                                      observe_token
                                      observe_token().report_construction
                                      observe_token().report_arrival_at
                                      observe_place().report_arrival_of
                                      observe_transition().got_enabled
                                      observe_transition().got_enabled
                                      observe_transition().after_firing
                                      observe_transition().before_firing
                                      observe_transition().after_firing
                                      observe_transition().before_firing
                                      observe_token().report_departure_from
                                      observe_place().report_departure_of
                                      observe_transition().got_disabled
                                      observe_transition().got_disabled
                                      observe_token().report_arrival_at
                                      observe_place().report_arrival_of
                                      observe_transition().got_enabled
                                      observe_transition().after_firing
                                      observe_transition().before_firing
                                      observe_token().report_departure_from
                                      observe_place().report_departure_of
                                      observe_transition().got_disabled
                                      observe_token().report_destruction
                                      observe_transition().after_firing
                                      """))

def fff(calls):
    return "\n".join(list(call[0] for call in calls))


if __name__ == '__main__':
    main()
