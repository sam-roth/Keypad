

from codeedit import buffer as buffer_


buf = buffer_.Buffer.from_text(
'''
int main(int argc, char **argv)
{
    return 0;
}
'''
)




curs = buf.cursor()
buf.canonical_cursor = curs
buf.dump()
#curs3 = buffer_.Cursor(buf)
#curs3.move_to(4, 0)

curs.move_to(2, 1)
buf.dump()
curs.insert('\n')
buf.dump()

curs.insert('''    std::cout << \n        "Hello, world!\\n";''')

buf.dump()

curs.move_by(right=-6)
buf.dump()
curs.move_by(right=6)
buf.dump()

#print(curs3.line, curs3.col)
ref = curs.clone()
curs.move_to(2, 1)
buf.dump()
curs.remove_until(buf.cursor(5, -1)) 



buf.dump()
#print(curs3.line, curs3.col)

