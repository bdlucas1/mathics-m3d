Manipulate[
    Plot[
        Abs[Zeta[x I + y]],
        {x,0,50}, PlotRange->{0,4}
    ],
    {{y,0.5},0,.95,0.05}
]
