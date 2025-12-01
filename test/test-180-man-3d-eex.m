Manipulate[
    Plot3D[
        {Exp[Exp[x + I y]], z},
        {x,-1.5,1.5}, {y,-6,6},
        PlotRange->{Automatic, Automatic, {-1,1.5}},
        BoxRatios->{1,1,1}, ViewPoint->{-2,-0.7,.7}
    ],
    {{z,1}, -1, 1.5, 0.05}
]
