Manipulate[
    ComplexPlot[
        Exp[Exp[z]]-k,
        {z,-1-10 I,3+10 I},
        PlotRange->{Automatic,Automatic,{0,4}},
        PlotPoints->{400,400}
    ],
    {{k,1},0,2,0.05}
]
