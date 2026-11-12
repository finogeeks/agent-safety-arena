"""Native readback keeps row boundaries after full-width console cells."""
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from arena.adapters.agents import windows_console as console


class NativeConsoleReadback(unittest.TestCase):
    def test_wide_characters_do_not_split_later_approval_rows(self):
        width,height=64,3
        first=[('错',0x100),('错',0x200)]*10+[(' ',0)]*44
        rows=[first]
        for text in ('Would you like to run the following command?', '› 1. Yes, proceed (y)'):
            rows.append([(char,0) for char in text]+[(' ',0)]*(width-len(text)))
        grid=[cell for row in rows for cell in row]
        kernel=MagicMock()
        kernel.AttachConsole.return_value=True
        kernel.CreateFileW.return_value=1
        def info(handle,pointer):
            pointer._obj.size.x=width;pointer._obj.size.y=height
            pointer._obj.window.top=0;pointer._obj.window.bottom=height-1
            return True
        kernel.GetConsoleScreenBufferInfo.side_effect=info
        def flattened(handle,buffer,count,origin,read):
            # Character-stream reads do not retain the wide trailing cells.
            value=''.join(char for char,flags in grid if not flags&0x200)
            buffer.value=value;read._obj.value=len(value)
            return True
        kernel.ReadConsoleOutputCharacterW.side_effect=flattened
        def cells(handle,buffer,size,origin,region):
            for index,(char,flags) in enumerate(grid):
                buffer[index].char.unicode=char;buffer[index].attributes=flags
            return True
        kernel.ReadConsoleOutputW.side_effect=cells
        with patch.object(console.c,'WinDLL',return_value=kernel,create=True):
            result=console.main(dict(pid=123,action='read'))
        self.assertIn('Would you like to run the following command?',result['text'].splitlines())
        self.assertIn('› 1. Yes, proceed (y)',result['text'].splitlines())


if __name__=='__main__':
    unittest.main()
