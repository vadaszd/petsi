from petsi import Net

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

        net.add_destructor("departures", "t1", "place 1")

        net.add_type("your type")
        net.add_place("place 3", "your type", "LIFO")
        with self.assertRaisesRegex(ValueError, "Type mismatch on TransferArc\\('transfers'\\): "
                                                "type\\(place 3\\) is Type\\('your type'\\) whereas "
                                                "type\\(place 1\\) is Type\\('my type'\\)"):
            net.add_transfer("transfers", "t1", "place 1", "place 3")

        net.add_transfer("transfers", "t1", "place 1", "place 2")

    def test_net_building_attaches_observers(self):
        net = Net("test net")
        net.add_type("my type")

        observer = Mock()
        observer.configure_mock(name='observer #1')
        observer.observe_place = Mock(return_value="place observer")
        observer.observe_transition = Mock(return_value="transition observer")

        net.register_observer(observer)
        with self.assertRaisesRegex(ValueError, "An observer with name 'observer #1' is already registered."):
            net.register_observer(observer)

        p1 = net.add_place("place 1", "my type", "FIFO")
        observer.observe_place.assert_called_with(p1)
        self.assertTrue("place observer" in p1._place_observers)

        t1 = net.add_immediate_transition("t1", 1, 1.)
        observer.observe_transition.assert_called_with(t1)
        self.assertTrue("transition observer" in t1._transition_observers)

        observer2 = Mock()
        observer2.configure_mock(name='observer #2')
        observer2.observe_place = Mock(return_value="place observer #2")
        observer2.observe_transition = Mock(return_value="transition observer #2")

        net.register_observer(observer2)
        observer2.observe_place.assert_called_with(p1)
        self.assertTrue("place observer #2" in p1._place_observers)
        observer2.observe_transition.assert_called_with(t1)
        self.assertTrue("transition observer #2" in t1._transition_observers)


if __name__ == '__main__':
    main()
