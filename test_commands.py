import unittest
from commands import parse_command, to_command, validate_source, needs_medicine_count

class CommandTests(unittest.TestCase):
    def test_roundtrip(self):
        for command in ['maa daily', 'maa test', 'maa run fight stage=OF-1 medicine=3', 'maa run base credit']:
            selection = parse_command(command)
            self.assertEqual(parse_command(to_command(selection)), selection)
    def test_shell_payload_rejected(self):
        for command in ['maa run fight stage=1-7;echo', 'maa run fight stage=$(id)', 'maa run fight stage=--help', 'maa run base stage=1-7', 'maa run fight stage=1-7 stage=CE-6']:
            with self.assertRaises(ValueError): parse_command(command)
    def test_medicine_grounding(self):
        selection = parse_command('maa run fight stage=1-7 medicine=2')
        validate_source(selection, '帮我在明日方舟吃两瓶理智药刷1-7')
        for message in ['帮我刷1-7', '帮我吃一瓶理智药刷1-7']:
            with self.assertRaises(ValueError): validate_source(selection, message)
    def test_stage_grounding(self):
        selection = parse_command('maa run fight stage=CE-6')
        validate_source(selection, '帮我刷CE-6')
        with self.assertRaises(ValueError): validate_source(selection, '帮我刷关卡')
    def test_ambiguous_medicine(self):
        self.assertTrue(needs_medicine_count('帮我在明日方舟吃几瓶理智药刷取关卡'))
        self.assertFalse(needs_medicine_count('帮我吃两瓶理智药刷1-7'))

if __name__ == '__main__': unittest.main()
