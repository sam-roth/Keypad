
struct Foo
{
    int _bar;
    float _baz;

    const int &bar() const
    {
        return _bar;
    }

    const float &baz() const
    {
        return _baz;
    }
};
