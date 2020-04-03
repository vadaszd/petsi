from petsi.Simulation import AutoFirePlugin
from petsi.Structure import Place
from inspect import cleandoc
from unittest import TestCase, main
from unittest.mock import Mock


class FireControlTest(TestCase):
    def setUp(self):
        self.fire_control = AutoFirePlugin.FireControl()
        self.immediate_transition1 = Mock(is_timed=False, priority=1, weight=1.1)
        self.immediate_transition2a = Mock(is_timed=False, priority=2, weight=0.0)
        self.immediate_transition2b = Mock(is_timed=False, priority=2, weight=1.0)
        self.timed_transition1 = Mock(is_timed=True, **{'get_duration.return_value': 1.1})
        self.timed_transition2 = Mock(is_timed=True, **{'get_duration.return_value': 2.3})

    def assert_next_transition_is(self, transition):
        self.assertIs(self.fire_control.select_next_transition()[1], transition)

    def test_firing_order(self):
        # No enabled transitions result in IndexError
        with self.assertRaises(IndexError):
            self.fire_control.select_next_transition()

        # Enable a single transition
        self.fire_control.enable_transition(self.immediate_transition1)

        # That should be the next to fire
        self.assert_next_transition_is(self.immediate_transition1)
        # Calls to select_next_transition() do not change the state of the fire control
        self.assert_next_transition_is(self.immediate_transition1)

        # Disabling the sole enabled transition causes IndexError when asking for an enabled one
        self.fire_control.disable_transition(self.immediate_transition1)
        with self.assertRaises(IndexError):
            self.fire_control.select_next_transition()

        # Immediate transitions are selected before timed ones
        self.fire_control.enable_transition(self.immediate_transition1)
        self.fire_control.enable_transition(self.timed_transition2)
        self.fire_control.enable_transition(self.timed_transition1)
        self.assert_next_transition_is(self.immediate_transition1)

        # Disabling a wrongly selected timed transition raises AssertionError
        with self.assertRaises(AssertionError):
            self.fire_control.disable_transition(self.timed_transition2)

        # High priority immediate transitions are selected before low ones
        self.fire_control.enable_transition(self.immediate_transition2a)
        self.assert_next_transition_is(self.immediate_transition2a)

        # For equal priority immediate transitions weights are considered
        self.fire_control.enable_transition(self.immediate_transition2b)
        self.assert_next_transition_is(self.immediate_transition2b)

        # Overall firing order and timing
        firing_order = [self.immediate_transition2b,
                        self.immediate_transition2a,
                        self.timed_transition1,
                        self.timed_transition2,
                        ]

        # Perturb the order of disabling the transitions
        self.fire_control.disable_transition(self.immediate_transition1)

        # Fire all enabled transition, validating the order enforced
        # by the fire control
        for transition in firing_order:
            self.assert_next_transition_is(transition)

            # Mimic firing by disabling
            self.fire_control.disable_transition(transition)


if __name__ == '__main__':
    main()
