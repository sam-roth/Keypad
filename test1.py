

from codeedit import buffer as buffer_


buf = buffer_.Buffer.from_text(
'''
int main(int argc, char **argv)
{

    return 0;
}
'''
)


buf.dump()


curs = buffer_.Cursor(buf)
curs3 = buffer_.Cursor(buf)

curs.move_to(3, 0)
curs.insert('''    std::cout << "Hello, world!\\n";''')

buf.dump()

curs.move_to(2, 1)

curs2 = buffer_.Cursor(buf)
curs2.move_to(4, 13)

curs.remove_until(curs2)

buf.dump()


