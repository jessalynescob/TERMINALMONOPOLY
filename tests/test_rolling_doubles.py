import io
import unittest
from contextlib import redirect_stdout

import banker
import monopoly_directory.monopoly as mply
from utils.utils import Client


class TestRollingDoubles(unittest.TestCase):

    def setUp(self):
        self.dice_to_roll = []
        self.messages = []
        self.ana = Client(None, 0, "Ana", None)
        self.ben = Client(None, 1, "Ben", None)
        with redirect_stdout(io.StringIO()):
            mply.start_game(1500, 2, ["Ana", "Ben"], [self.ana, self.ben])
        mply.turn = 0
        mply.history.clear()
        self.real_roll = mply.roll
        self.real_send_notif = banker.net.send_notif
        mply.roll = self.fake_roll
        banker.net.send_notif = self.fake_send_notif

    def tearDown(self):
        mply.roll = self.real_roll
        banker.net.send_notif = self.real_send_notif

    def fake_roll(self):
        return self.dice_to_roll.pop(0)

    def fake_send_notif(self, socket, message, header):
        self.messages.append(message)

    def send(self, client, action):
        with redirect_stdout(io.StringIO()):
            banker.monopoly_game(client, "mply," + action)

    def test_doubles_lets_player_roll_again(self):
        self.dice_to_roll = [(3, 3), (1, 2)]

        self.send(self.ana, "roll")
        self.assertTrue(self.ana.can_roll)
        self.assertEqual(mply.players[0].location, 6)
        self.assertIn("roll again", self.messages[-1])

        self.send(self.ana, "roll")
        self.assertFalse(self.ana.can_roll)
        self.assertEqual(mply.players[0].location, 9)
        self.assertIn("e to end turn", self.messages[-1])

    def test_not_doubles_ends_rolling(self):
        self.dice_to_roll = [(1, 2)]

        self.send(self.ana, "roll")
        self.assertFalse(self.ana.can_roll)
        self.assertFalse(self.messages[-1].startswith("player_choice"))

    def test_three_doubles_sends_player_to_jail(self):
        self.dice_to_roll = [(3, 3), (4, 4), (5, 5)]

        self.send(self.ana, "roll")
        self.send(self.ana, "roll")
        self.send(self.ana, "roll")

        self.assertTrue(mply.players[0].jail)
        self.assertEqual(mply.players[0].location, 10)
        self.assertIn(0, mply.board.locations[10].players)
        self.assertNotIn(0, mply.board.locations[14].players)
        self.assertFalse(self.ana.can_roll)

    def test_doubles_onto_go_to_jail_ends_rolling(self):
        mply.board.update_location(mply.players[0], 0, 22)
        self.dice_to_roll = [(4, 4)]

        self.send(self.ana, "roll")

        self.assertTrue(mply.players[0].jail)
        self.assertEqual(mply.players[0].location, 10)
        self.assertIn(0, mply.board.locations[10].players)
        self.assertNotIn(0, mply.board.locations[30].players)
        self.assertFalse(self.ana.can_roll)

    def test_buying_after_doubles_still_lets_player_roll_again(self):
        self.dice_to_roll = [(3, 3)]

        self.send(self.ana, "roll")
        self.send(self.ana, "trybuy")

        self.assertTrue(self.ana.can_roll)

    def test_roll_count_starts_over_next_turn(self):
        self.dice_to_roll = [(1, 2)]

        self.send(self.ana, "roll")
        self.send(self.ana, "endturn")

        self.assertEqual(self.ana.num_rolls, 0)

    def test_doubles_in_jail_frees_player_without_extra_roll(self):
        mply.board.locations[0].players.remove(0)
        mply.board.locations[10].players.append(0)
        mply.players[0].go_to_jail()
        self.dice_to_roll = [(2, 2)]

        self.send(self.ana, "roll")

        self.assertFalse(mply.players[0].jail)
        self.assertEqual(mply.players[0].location, 14)
        self.assertFalse(self.ana.can_roll)

    def test_no_doubles_in_jail_keeps_player_in_jail(self):
        mply.board.locations[0].players.remove(0)
        mply.board.locations[10].players.append(0)
        mply.players[0].go_to_jail()
        self.dice_to_roll = [(1, 2)]

        self.send(self.ana, "roll")

        self.assertTrue(mply.players[0].jail)
        self.assertEqual(mply.players[0].location, 10)
        self.assertFalse(self.ana.can_roll)


if __name__ == "__main__":
    unittest.main()
